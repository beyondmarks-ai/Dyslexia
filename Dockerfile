FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
WORKDIR /app

COPY requirements.txt requirements-azure.txt ./
RUN pip install --no-cache-dir -r requirements-azure.txt
COPY . .

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
