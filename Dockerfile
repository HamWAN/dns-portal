# syntax=docker/dockerfile:1.4
ARG PYTHON_VERSION=3
FROM python:$PYTHON_VERSION
EXPOSE 8000
WORKDIR /app 
COPY requirements.txt /app
COPY config.template /app/config
COPY deploy.template /app/deploy
RUN pip3 install -r requirements.txt --no-cache-dir
COPY . /app 
ENTRYPOINT ["python"] 
CMD ["manage.py", "runserver", "0.0.0.0:8000"]
