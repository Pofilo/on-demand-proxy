# Same official python image but without restrictions of official docker registry
FROM registry.pofilo.fr/python:3.14.3-alpine3.23

LABEL maintainer="Pofilo <git@pofilo.fr>"

ENV PYTHONUNBUFFERED=1

WORKDIR /ondemandproxy
COPY . .
RUN pip install . --root-user-action=ignore && rm -fr /ondemandproxy

ENTRYPOINT ["ondemandproxy"]
