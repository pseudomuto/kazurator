FROM openjdk:8-jre-alpine
MAINTAINER David Muto <david.muto@gmail.com>
ENV REFRESHED_AT 2017-01-04

ADD target/scala-2.11/curator.jar /

ENTRYPOINT ["java"]
CMD ["-jar", "/curator.jar"]
