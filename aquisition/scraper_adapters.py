import os
import subprocess
import json
import hashlib
import pathlib
import shutil
import sys
import time
import re
import uuid
import signal
import threading
import queue
import requests
import numpy as np
from typing import Tuple, Optional, List
from data_contracts import RawPageBundle


def _get_npx_path() -> str:
    if sys.platform.startswith('win32'):
        npx_path = shutil.which("npx.cmd")
        if npx_path:
            return npx_path
        npx_path = shutil.which("npx.ps1")
        if npx_path:
            return npx_path
        common_paths = [
            r"C:\Program Files\nodejs\npx.cmd",
            r"C:\Program Files\nodejs\npx.ps1",
            r"C:\Program Files (x86)\nodejs\npx.cmd",
            r"C:\Program Files (x86)\nodejs\npx.ps1",
            os.path.expandvars(r"%APPDATA%\npm\npx.cmd"),
            os.path.expandvars(r"%APPDATA%\npm\npx.ps1")
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    npx_path = shutil.which("npx")
    if npx_path:
        return npx_path
    raise RuntimeError("npx not found. Please install Node.js and restart your terminal.")


def _quote_cmd_arg(arg: str) -> str:
    result = []
    n_backslashes = 0
    for ch in arg:
        if ch == "\\":
            n_backslashes += 1
            continue
        if ch == '"':
            result.append("\\" * (n_backslashes * 2 + 1))
            result.append('"')
        else:
            result.append("\\" * n_backslashes)
            result.append(ch)
        n_backslashes = 0
    result.append("\\" * n_backslashes)
    return '"' + "".join(result) + '"'


def _build_windows_cmdline(cmd_parts) -> str:
    return " ".join(_quote_cmd_arg(part) for part in cmd_parts)


def _needs_cmd_shell_quoting(executable: str) -> bool:
    return sys.platform.startswith("win32") and executable.lower().endswith((".cmd", ".bat"))


def _popen_kwargs_for_new_process_group() -> dict:
    if sys.platform.startswith("win32"):
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"preexec_fn": os.setsid}


def _kill_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if sys.platform.startswith("win32"):
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
            process.wait(timeout=5)
        except Exception:
            pass


def _cleanup_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def run_cli(args, output_file=None):
    npx_path = _get_npx_path()
    cmd = [npx_path, "--yes", "--package", "@brightdata/cli", "brightdata"] + args
    print("\n$ " + " ".join(cmd))

    if _needs_cmd_shell_quoting(npx_path):
        result = subprocess.run(_build_windows_cmdline(cmd), capture_output=True, text=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"CLI failed: {result.stderr}")
    if output_file:
        if not os.path.exists(output_file):
            raise RuntimeError(f"Output file not created: {output_file}")
        with open(output_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return result.stdout


def fit_line(x, y):
    x = np.array(x)
    y = np.array(y)
    if len(x) < 2 or np.all(y == 0):
        return 0, 0
    a, b = np.polyfit(x, y, 1)
    return a, b


class ScraperAdapter:
    def fetch(self, url: str) -> Tuple[str, int]:
        raise NotImplementedError


class DirectHTTPAdapter(ScraperAdapter):
    def __init__(self, timeout: int = 10):
        import requests
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def fetch(self, url: str) -> Tuple[str, int]:
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text, response.status_code
        except Exception as e:
            print(f"⚠️  DirectHTTP error: {e}")
            return "", 503


class BrightDataCLIAdapter(ScraperAdapter):
    def __init__(
        self,
        api_key: Optional[str] = None,
        fields: Optional[List[str]] = None,
        max_pages: Optional[int] = None,
        target_records: Optional[int] = None,
        sample_durations: List[int] = None,
        safety_factor: float = 1.2
    ):
        self.api_key = (
            api_key
            or os.getenv("BRIGHTDATA_API_KEY")
            or os.getenv("BRIGHTDATA_API_TOKEN")
        )
        self.fields = fields or ["Product Title", "Price", "Rating", "Number of Reviews", "Currency"]
        self.max_pages = max_pages
        self.target_records = target_records
        self.sample_durations = sample_durations or [60, 90, 120]
        self.safety_factor = safety_factor

        self.cache_dir = pathlib.Path(".brightdata_cache")
        self.cache_dir.mkdir(exist_ok=True)

        if not self.api_key:
            print(
                "⚠️  No Bright Data API key found (checked BRIGHTDATA_API_KEY and "
                "BRIGHTDATA_API_TOKEN env vars, and the api_key argument). "
                "Falling back to direct HTTP — this will NOT honor target_records, "
                "pagination, or field extraction."
            )
            self.fallback = DirectHTTPAdapter()
        else:
            self.fallback = None
            os.environ["BRIGHTDATA_API_KEY"] = self.api_key

    # ============================================================
    # EXACT DESCRIPTION FORMAT (as requested)
    # ============================================================
    def _build_description(self) -> str:
        fields_str = ", ".join(self.fields)
        return (
            f"Extract ONLY these fields: {fields_str}. "
            "Do not extract any other data. "
            "Preserve exact values from the webpage. "
            "Use null if a field is unavailable. "
            "Return structured JSON."
        )

    def _get_collector_id(self, url: str, description: str) -> str:
        cache_key = hashlib.sha256(f"{url}|{description}".encode()).hexdigest()[:16]
        cache_file = self.cache_dir / f"collector_{cache_key}.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                cached = json.load(f)
            print(f"♻️  Reusing existing collector: {cached['collector_id']}")
            return cached["collector_id"]

        print("🚀 Creating new Bright Data scraper via npx...")
        create_file = f"collector_create_{uuid.uuid4().hex}.json"
        try:
            create_result = run_cli(
                [
                    "scraper",
                    "create",
                    url,
                    description,
                    "--name",
                    "auto-scraper",
                    "-o",
                    create_file
                ],
                output_file=create_file
            )
            collector_id = create_result.get("collector_id")
            if not collector_id:
                raise RuntimeError("No collector_id returned.")

            # --- Wait a bit for the collector to become active ---
            print("⏳ Waiting 15 seconds for the collector to activate...")
            time.sleep(15)

            cache_file.write_text(json.dumps({"collector_id": collector_id}))
            print(f"✅ Collector created: {collector_id}")
            return collector_id
        except Exception as e:
            if cache_file.exists():
                cache_file.unlink()
            raise RuntimeError(f"Scraper creation failed: {e}")
        finally:
            _cleanup_file(create_file)

    # ============================================================
    # FIX: thread reader – handle closed stdout
    # ============================================================
    def _extract_job_id(self, process: subprocess.Popen, timeout: float = 30) -> Optional[str]:
        line_queue: "queue.Queue[Optional[str]]" = queue.Queue()

        def _reader():
            try:
                for line in process.stdout:
                    line_queue.put(line)
            except (ValueError, OSError):
                # stdout was closed, exit gracefully
                pass
            finally:
                line_queue.put(None)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        job_id = None
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                line = line_queue.get(timeout=remaining)
            except queue.Empty:
                break
            if line is None:
                break
            print(line.strip())
            match = re.search(r'(?:Job ID|Batch job):\s*(\S+)', line)
            if not match:
                match = re.search(r'response_id:\s*([^)\s]+)', line)
            if match:
                job_id = match.group(1)
                break

        return job_id

    # ============================================================
    # FIX: wait for output file to be complete after cancellation
    # ============================================================
    def _run_and_cancel(self, collector_id: str, url: str, wait_seconds: float, output_file: Optional[str] = None):
        if output_file is None:
            output_file = f"brightdata_run_{uuid.uuid4().hex}.json"

        npx_path = _get_npx_path()
        cmd = [
            npx_path, "--yes", "--package", "@brightdata/cli",
            "brightdata", "scraper", "run",
            collector_id, url,
            "--pretty",
            "-o", output_file
        ]
        print("\n🚀 Starting: " + " ".join(cmd))
        popen_args = _build_windows_cmdline(cmd) if _needs_cmd_shell_quoting(npx_path) else cmd
        process = subprocess.Popen(
            popen_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            **_popen_kwargs_for_new_process_group()
        )

        try:
            job_id = self._extract_job_id(process, timeout=30)

            if not job_id:
                for _ in range(5):
                    if process.poll() is not None:
                        break
                    time.sleep(1)
                # If the process finished and we still couldn't get a job id,
                # try to read the output file (maybe it completed quickly).
                if os.path.exists(output_file):
                    try:
                        with open(output_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        _cleanup_file(output_file)
                        return data
                    except:
                        pass
                raise RuntimeError("Could not extract Job ID from CLI output.")

            print(f"✅ Extracted Job ID: {job_id}")

            elapsed = 0
            while elapsed < wait_seconds:
                time.sleep(2)
                elapsed += 2
                process.poll()
                if process.returncode is not None:
                    print("✅ Job finished early. Skipping cancel.")
                    break
            else:
                cancel_url = f"https://api.brightdata.com/dca/jobs/{job_id}/cancel"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                print(f"🛑 Cancelling job via API: {cancel_url}")
                try:
                    resp = requests.post(cancel_url, headers=headers, timeout=15)
                    print(f"   Cancel response: {resp.status_code} - {resp.text}")
                except requests.RequestException as e:
                    print(f"⚠️  Cancel request failed: {e}")

            try:
                process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                print("⚠️  Process didn't exit after cancel; terminating it locally.")
        finally:
            _kill_process_tree(process)

        # --- Wait for the output file to become readable and contain data ---
        if os.path.exists(output_file):
            for _ in range(10):  # wait up to ~10 seconds
                time.sleep(0.5)
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # If data is a non‑empty list or dict, we're good
                    if data:
                        _cleanup_file(output_file)
                        return data
                except (json.JSONDecodeError, OSError):
                    continue
            # One final attempt
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    _cleanup_file(output_file)
                    return data
            except:
                pass

        return None

    def _warmup_scraper(self, url: str, collector_id: str, run_tag: str, warmup_durations: List[int] = None) -> None:
        warmup_durations = warmup_durations or [30, 40]
        print(f"\n🔥 WARM-UP PHASE: Priming scraper with {len(warmup_durations)} test run(s) (results discarded)")
        for i, t in enumerate(warmup_durations, 1):
            print(f"\n--- Warm-up {i}/{len(warmup_durations)}: running for {t} seconds (not used for rate calc) ---")
            warmup_data = self._run_and_cancel(collector_id, url, t, f"warmup_{run_tag}_{t}s.json")
            warmup_count = len(warmup_data) if warmup_data else 0
            print(f"   Warm-up retrieved {warmup_count} records in {t}s (discarded, not counted).")

    def _estimate_rate(self, url: str, collector_id: str, run_tag: str) -> Tuple[float, float, List[dict]]:
        self._warmup_scraper(url, collector_id, run_tag)

        print("\n📊 ESTIMATION PHASE: Running sample batches")
        sample_times = self.sample_durations
        record_counts = []
        sample_data = []
        a, b = 0, 0

        for i, t in enumerate(sample_times, 1):
            print(f"\n--- Sample {i}/{len(sample_times)}: running for {t} seconds ---")
            data = self._run_and_cancel(collector_id, url, t, f"sample_{run_tag}_{t}s.json")
            count = len(data) if data else 0
            record_counts.append(count)
            sample_data.append(data if data else [])
            print(f"   Retrieved {count} records in {t} seconds.")

            if self.target_records and count >= self.target_records:
                print(f"✅ Already got {count} records (target: {self.target_records}). Stopping estimation early.")
                total_records = sum(record_counts)
                total_time = sum(sample_times[:i])
                rate = total_records / total_time if total_time > 0 else 0
                if rate <= 0:
                    raise RuntimeError("No data retrieved. Increase sample durations or check URL.")
                return rate, 0, sample_data

        a, b = fit_line(sample_times, record_counts)
        if a <= 0:
            print("⚠️  Slope zero/negative; using average rate.")
            total_records = sum(record_counts)
            total_time = sum(sample_times)
            rate = total_records / total_time if total_time > 0 else 0
            if rate <= 0:
                raise RuntimeError("No data retrieved. Increase sample durations or check URL.")
            return rate, 0, sample_data
        else:
            overhead = max(0, -b / a)
            return a, overhead, sample_data

    def fetch(self, url: str) -> Tuple[str, int]:
        if self.fallback:
            return self.fallback.fetch(url)

        description = self._build_description()
        collector_id = self._get_collector_id(url, description)

        run_tag = uuid.uuid4().hex[:8]

        if self.target_records is not None:
            print(f"🎯 Target records: {self.target_records}")
            rate, overhead, sample_data = self._estimate_rate(url, collector_id, run_tag)
            print(f"📈 Effective rate: {rate:.4f} rec/s, overhead: {overhead:.2f}s")
            target_time = (self.target_records / rate) * self.safety_factor + overhead
            print(f"⏱️  Computed run time: {target_time:.2f}s")

            total_samples = 0
            for data in sample_data:
                total_samples += len(data)
            if total_samples >= self.target_records:
                print("✅ Already have enough records from sample batches. Using sample data.")
                merged = []
                for data in sample_data:
                    merged.extend(data)
                if len(merged) > self.target_records:
                    merged = merged[:self.target_records]
                return json.dumps(merged, ensure_ascii=False), 200

            print("\n📦 Running final scrape...")
            final_data = self._run_and_cancel(collector_id, url, target_time, f"phase2_output_{run_tag}.json")
            if final_data is None:
                raise RuntimeError("Final scrape returned no data.")
            if len(final_data) > self.target_records:
                final_data = final_data[:self.target_records]
            return json.dumps(final_data, ensure_ascii=False), 200

        print("⚠️  No target_records set; running default 30s scrape.")
        data = self._run_and_cancel(collector_id, url, 30, f"default_output_{run_tag}.json")
        if data is None:
            return json.dumps([]), 503
        return json.dumps(data, ensure_ascii=False), 200


def select_scraper_adapter(target_domain: str, config) -> ScraperAdapter:
    if config.scraper == "brightdata":
        fields = getattr(config, "fields", None)
        max_pages = getattr(config, "max_pages", None)
        target_records = getattr(config, "target_records", None)
        sample_durations = getattr(config, "sample_durations", [60, 90, 120])
        safety_factor = getattr(config, "safety_factor", 1.2)
        api_key = (
            getattr(config, "brightdata_api_key", None)
            or os.getenv("BRIGHTDATA_API_KEY")
            or os.getenv("BRIGHTDATA_API_TOKEN")
        )
        return BrightDataCLIAdapter(
            api_key=api_key,
            fields=fields,
            max_pages=max_pages,
            target_records=target_records,
            sample_durations=sample_durations,
            safety_factor=safety_factor
        )
    return DirectHTTPAdapter()