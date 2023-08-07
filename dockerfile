FROM python:3.11.2-alpine

LABEL author="var211"

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV APP_HOME /opt/djangoapp
ENV PYTHONPATH /opt/djangoapp
ENV DJANGO_SETTINGS_MODULE nftmarket.app.settings

RUN mkdir -p /opt/djangoapp/nftmarket

WORKDIR $APP_HOME

COPY requirements.txt .
COPY django-bootstrap.sh .

RUN chmod +x /opt/djangoapp/django-bootstrap.sh
RUN pip install -r requirements.txt

ENTRYPOINT /opt/djangoapp/django-bootstrap.sh
