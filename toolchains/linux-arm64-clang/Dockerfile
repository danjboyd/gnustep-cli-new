FROM debian:13

# Debian 13 "trixie" is the pinned build base for the linux-arm64-clang managed
# toolchain. It provides glibc 2.41 and ICU 76; GNUstep libs-base/libs-corebase
# link against the versioned ICU SONAMEs (libicui18n.so.76, libicuuc.so.76,
# libicudata.so.76), so the produced artifact runs on Debian 13 and other
# distributions shipping the same ICU major. Debian 12 "bookworm" (ICU 72) is
# deprecated and intentionally no longer the build base. Build this image on an
# aarch64 host so the produced toolchain targets arm64.

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
        autoconf \
        automake \
        libtool \
        python3 \
        clang \
        lld \
        libblocksruntime-dev \
        libssl-dev \
        zlib1g-dev \
        libfreetype-dev \
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
