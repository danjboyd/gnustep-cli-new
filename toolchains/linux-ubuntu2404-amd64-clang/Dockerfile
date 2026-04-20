FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        tar \
        gzip \
        xz-utils \
        zstd \
        make \
        cmake \
        ninja-build \
        pkg-config \
        clang \
        lld \
        libxml2-dev \
        libxslt1-dev \
        libicu-dev \
        libavahi-client-dev \
        libcurl4-gnutls-dev \
        libgnutls28-dev \
        libffi-dev \
        libjpeg-dev \
        libtiff-dev \
        libpng-dev \
        libcairo2-dev \
        libxft-dev \
        libxt-dev \
        libx11-dev \
        libxext-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY build-toolchain.sh /usr/local/bin/build-gnustep-toolchain
RUN chmod +x /usr/local/bin/build-gnustep-toolchain

CMD ["/usr/local/bin/build-gnustep-toolchain"]
