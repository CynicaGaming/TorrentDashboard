FROM python:3.12-slim
WORKDIR /app
COPY . /app
EXPOSE 8765
CMD ["python", "dashboard.py", "--no-browser"]
