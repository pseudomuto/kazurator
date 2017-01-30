FROM python:3.6-alpine
MAINTAINER David Muto <david.muto@gmail.com>
ENV REFRESHED_AT 2017-01-27

RUN pip install --upgrade pip
RUN pip install termcolor && mkdir -p /kazoom

ADD ./kazurator-*.whl ./
ADD ./kazoom ./kazoom
RUN pip install kazurator-*.whl

ENTRYPOINT ["python"]
CMD ["-m", "kazoom"]
