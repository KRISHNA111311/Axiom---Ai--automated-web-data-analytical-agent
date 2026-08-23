"""
Phase 8: Privacy Boundary Broker (M4)
BRK-1, BRK-2, BRK-3
"""

import os
import json
import time
import duckdb
import pandas as pd
from typing import Dict, Any, List
from multiprocessing import Process, connection
from multiprocessing.connection import Listener, Client


class BrokerProcess:
    """The actual broker process that holds the DuckDB connection."""

    def __init__(self, db_path: str, address: tuple):
        self.db_path = db_path
        self.address = address
        self.conn = None

    def _init_db(self):
        """Initialize DuckDB connection and table if needed."""
        self.conn = duckdb.connect(self.db_path)
        # Create table if not exists (schema matches SanitizedRecord)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scraped_records (
                title VARCHAR,
                category VARCHAR,
                price DOUBLE,
                currency VARCHAR,
                rating INTEGER,
                availability VARCHAR,
                source_url VARCHAR
            )
        """)

    def _ingest_records(self, records: List[Dict]) -> Dict:
        """Ingest a list of records into DuckDB, padding missing columns with None."""
        if not records:
            return {"row_count": 0, "column_count": 7, "warnings": ["No records provided."]}

        required_columns = ["title", "category", "price", "currency", "rating", "availability", "source_url"]
        padded_records = []
        for rec in records:
            padded = {}
            for col in required_columns:
                padded[col] = rec.get(col, None)   # default to None for missing fields
            padded_records.append(padded)

        df = pd.DataFrame(padded_records)
        # Ensure column order matches the table schema
        df = df[required_columns]

        self.conn.execute("DELETE FROM scraped_records")
        self.conn.execute("INSERT INTO scraped_records SELECT * FROM df")
        row_count = self.conn.execute("SELECT COUNT(*) FROM scraped_records").fetchone()[0]
        return {"row_count": row_count, "column_count": len(df.columns), "warnings": []}

    def _get_schema(self) -> Dict:
        """Return column names, types, and null ratios."""
        cols = self.conn.execute("PRAGMA table_info(scraped_records)").fetchall()
        total_rows = self.conn.execute("SELECT COUNT(*) FROM scraped_records").fetchone()[0]
        columns = []
        if total_rows == 0:
            for col in cols:
                columns.append({"name": col[1], "dtype": col[2], "null_ratio": 0.0})
        else:
            for col in cols:
                name = col[1]
                null_count = self.conn.execute(f"SELECT COUNT(*) FROM scraped_records WHERE {name} IS NULL").fetchone()[0]
                columns.append({"name": name, "dtype": col[2], "null_ratio": null_count / total_rows})
        return {"table_name": "scraped_records", "columns": columns, "row_count": total_rows}

    def _get_missing_values(self) -> Dict:
        """Return missing value ratios for each column."""
        total = self.conn.execute("SELECT COUNT(*) FROM scraped_records").fetchone()[0]
        if total == 0:
            return {}
        cols = self.conn.execute("PRAGMA table_info(scraped_records)").fetchall()
        result = {}
        for col in cols:
            name = col[1]
            null_count = self.conn.execute(f"SELECT COUNT(*) FROM scraped_records WHERE {name} IS NULL").fetchone()[0]
            result[name] = null_count / total
        return result

    def _get_correlations(self, columns: List[str]) -> Dict:
        """Return correlation matrix for numeric columns."""
        if len(columns) < 2:
            return {"matrix": {}, "columns": columns}
        # Filter to numeric columns that exist
        numeric_cols = []
        for col in columns:
            try:
                self.conn.execute(f"SELECT {col} FROM scraped_records LIMIT 1")
                numeric_cols.append(col)
            except:
                pass
        if len(numeric_cols) < 2:
            return {"matrix": {}, "columns": numeric_cols}
        matrix = {}
        for i, col1 in enumerate(numeric_cols):
            matrix[col1] = {}
            for j, col2 in enumerate(numeric_cols):
                if i == j:
                    matrix[col1][col2] = 1.0
                else:
                    result = self.conn.execute(f"SELECT CORR({col1}, {col2}) FROM scraped_records").fetchone()[0]
                    matrix[col1][col2] = result if result is not None else 0.0
        return {"matrix": matrix, "columns": numeric_cols}

    def _get_binned_stats(self, column: str, bins: int) -> Dict:
        """Return binned statistics for a numeric column using DuckDB's HISTOGRAM."""
        # DuckDB's HISTOGRAM(column) returns a MAP of bin edges to counts
        query = f"SELECT HISTOGRAM({column}) FROM scraped_records"
        result = self.conn.execute(query).fetchone()[0]
        if result is None or len(result) == 0:
            return {"column": column, "bin_edges": [], "counts": []}
        # result is a dict with keys as strings (bin edges), values as counts
        # Convert keys to float and sort
        items = sorted([(float(k), v) for k, v in result.items()])
        edges = [item[0] for item in items]
        counts = [item[1] for item in items]
        return {"column": column, "bin_edges": edges, "counts": counts}

    def _get_group_statistics(self, group_col: str, value_col: str) -> Dict:
        """Return mean, median, std, skewness, kurtosis per group."""
        query = f"""
            SELECT 
                {group_col} as group_name,
                COUNT(*) as n,
                AVG({value_col}) as mean,
                MEDIAN({value_col}) as median,
                STDDEV_SAMP({value_col}) as std,
                SKEWNESS({value_col}) as skewness,
                KURTOSIS({value_col}) as kurtosis
            FROM scraped_records
            GROUP BY {group_col}
        """
        result = self.conn.execute(query).fetchall()
        groups = []
        for row in result:
            groups.append({
                "group_name": row[0],
                "n": row[1],
                "mean": row[2],
                "median": row[3],
                "std": row[4],
                "skewness": row[5] if row[5] is not None else 0.0,
                "kurtosis": row[6] if row[6] is not None else 0.0,
                "variance": row[4] ** 2 if row[4] is not None else 0.0
            })
        return {"group_column": group_col, "value_column": value_col, "groups": groups}

    def _get_class_balance(self, label_col: str) -> Dict:
        """Return class counts and imbalance ratio."""
        counts = self.conn.execute(f"SELECT {label_col}, COUNT(*) FROM scraped_records GROUP BY {label_col}").fetchall()
        class_counts = {row[0]: row[1] for row in counts}
        if len(class_counts) < 2:
            return {"label_column": label_col, "class_counts": class_counts, "imbalance_ratio": 0.0}
        counts_list = list(class_counts.values())
        majority = max(counts_list)
        minority = min(counts_list)
        ratio = majority / minority if minority > 0 else float('inf')
        return {"label_column": label_col, "class_counts": class_counts, "imbalance_ratio": ratio}

    def _get_stationarity_inputs(self, time_col: str, value_col: str) -> Dict:
        """Return rolling mean, rolling variance, and lag-1 autocorrelation."""
        # We need ordered data by time
        query = f"SELECT {time_col}, {value_col} FROM scraped_records ORDER BY {time_col}"
        rows = self.conn.execute(query).fetchall()
        if len(rows) < 10:
            return {"time_column": time_col, "value_column": value_col, "rolling_mean_by_bucket": [], "rolling_var_by_bucket": [], "lag1_autocorr": 0.0}
        values = [row[1] for row in rows]
        # Compute rolling mean and variance with window 3 (simple)
        import numpy as np
        rolling_mean = np.convolve(values, np.ones(3)/3, mode='valid').tolist()
        rolling_var = []
        for i in range(len(values)-2):
            window = values[i:i+3]
            rolling_var.append(np.var(window))
        # lag-1 autocorrelation
        lag1 = np.corrcoef(values[:-1], values[1:])[0,1] if len(values) > 1 else 0.0
        return {
            "time_column": time_col,
            "value_column": value_col,
            "rolling_mean_by_bucket": rolling_mean,
            "rolling_var_by_bucket": rolling_var,
            "lag1_autocorr": lag1
        }

    def _export_snapshot(self, file_path: str) -> Dict:
        """Export the table as a Parquet file for the sandbox."""
        self.conn.execute(f"COPY scraped_records TO '{file_path}' (FORMAT PARQUET)")
        return {"file_path": file_path}

    def handle_request(self, request: Dict) -> Dict:
        """BRK-2: Handle a single request."""
        op = request.get("operation")
        params = request.get("params", {})

        # Allow-list of operations
        allowed_ops = [
            "ingest_records",
            "get_schema",
            "get_missing_values",
            "get_correlations",
            "get_binned_statistics",
            "get_group_statistics",
            "get_class_balance",
            "get_stationarity_inputs",
            "export_snapshot"
        ]
        if op not in allowed_ops:
            return {"ok": False, "error": f"Operation '{op}' not allowed."}

        try:
            if op == "ingest_records":
                result = self._ingest_records(params.get("records", []))
            elif op == "get_schema":
                result = self._get_schema()
            elif op == "get_missing_values":
                result = self._get_missing_values()
            elif op == "get_correlations":
                result = self._get_correlations(params.get("columns", []))
            elif op == "get_binned_statistics":
                result = self._get_binned_stats(params.get("column"), params.get("bins", 10))
            elif op == "get_group_statistics":
                result = self._get_group_statistics(params.get("group_column"), params.get("value_column"))
            elif op == "get_class_balance":
                result = self._get_class_balance(params.get("label_column"))
            elif op == "get_stationarity_inputs":
                result = self._get_stationarity_inputs(params.get("time_column"), params.get("value_column"))
            elif op == "export_snapshot":
                result = self._export_snapshot(params.get("file_path", "snapshot.parquet"))
            else:
                result = {"error": "Unhandled operation"}
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def run(self):
        """BRK-1: Start the broker process loop."""
        self._init_db()
        listener = Listener(self.address)
        print(f"🔒 Broker listening on {self.address}")
        while True:
            conn = listener.accept()
            try:
                request = conn.recv()
                response = self.handle_request(request)
                conn.send(response)
            except Exception as e:
                print(f"Broker error: {e}")
            finally:
                conn.close()


# ============================================================
# Wrapper functions for the orchestrator
# ============================================================

def start_broker_process(db_path: str, address: tuple = ('localhost', 6000)) -> tuple:
    """
    BRK-1: Start the broker process and return (process, address).
    """
    broker = BrokerProcess(db_path, address)
    p = Process(target=broker.run)
    p.daemon = True
    p.start()
    # Wait a moment for the listener to start
    time.sleep(0.5)
    return p, address


def broker_client_call(operation: str, params: Dict, address: tuple = ('localhost', 6000)) -> Dict:
    """
    BRK-3: Make an RPC call to the broker.
    Returns the 'result' part if successful, raises on error.
    """
    try:
        with Client(address) as client:
            client.send({"operation": operation, "params": params})
            response = client.recv()
            if response.get("ok"):
                return response.get("result", {})
            else:
                raise RuntimeError(f"Broker error: {response.get('error', 'Unknown error')}")
    except ConnectionRefusedError:
        raise RuntimeError("Broker not running. Call start_broker_process first.")