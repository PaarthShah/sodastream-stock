FROM python:3.11
LABEL authors="PaarthShah"

COPY --link requirements.txt .
RUN pip install -r requirements.txt

COPY --link sodastream.py .

ENTRYPOINT python sodastream.py