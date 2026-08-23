FROM python:3.11-slim

RUN pip install --no-cache-dir \
    pandas \
    pyarrow \
    matplotlib \
    seaborn \
    scipy \
    scikit-learn \
    statsmodels

WORKDIR /workspace
