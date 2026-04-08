#!/bin/sh
set -eu

PREFIX="/opt/gnustep-cli"
SOURCES_DIR="/var/tmp/gnustep-cli-openbsd/sources"
BUILD_ROOT="/var/tmp/gnustep-cli-openbsd/build"
HOST_OS="openbsd"
JOBS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)"

mkdir -p "$PREFIX" "$SOURCES_DIR" "$BUILD_ROOT"

if [ ! -d "$SOURCES_DIR/libobjc2/.git" ]; then
  git clone "https://github.com/gnustep/libobjc2.git" "$SOURCES_DIR/libobjc2"
fi
git -C "$SOURCES_DIR/libobjc2" fetch --tags origin
git -C "$SOURCES_DIR/libobjc2" checkout --detach "b67709ad7851973fde127022d8ac6a710c82b1d5"

if [ ! -d "$SOURCES_DIR/libdispatch/.git" ]; then
  git clone "https://github.com/swiftlang/swift-corelibs-libdispatch.git" "$SOURCES_DIR/libdispatch"
fi
git -C "$SOURCES_DIR/libdispatch" fetch --tags origin
git -C "$SOURCES_DIR/libdispatch" checkout --detach "4ce40128f607a6eb7b58077a06b7464c1518a30d"

if [ ! -d "$SOURCES_DIR/tools-make/.git" ]; then
  git clone "https://github.com/gnustep/tools-make.git" "$SOURCES_DIR/tools-make"
fi
git -C "$SOURCES_DIR/tools-make" fetch --tags origin
git -C "$SOURCES_DIR/tools-make" checkout --detach "50cf9619e672fb2ff6825f239b5a172c5dc55630"

if [ ! -d "$SOURCES_DIR/libs-base/.git" ]; then
  git clone "https://github.com/gnustep/libs-base.git" "$SOURCES_DIR/libs-base"
fi
git -C "$SOURCES_DIR/libs-base" fetch --tags origin
git -C "$SOURCES_DIR/libs-base" checkout --detach "d898f703e618b86f9b7ecb0f05a257cb6ed3ffac"

if [ ! -d "$SOURCES_DIR/libs-corebase/.git" ]; then
  git clone "https://github.com/gnustep/libs-corebase.git" "$SOURCES_DIR/libs-corebase"
fi
git -C "$SOURCES_DIR/libs-corebase" fetch --tags origin
git -C "$SOURCES_DIR/libs-corebase" checkout --detach "e5983493d5ddf9c5b7e562f166855d9517a3f179"

if [ ! -d "$SOURCES_DIR/libs-gui/.git" ]; then
  git clone "https://github.com/gnustep/libs-gui.git" "$SOURCES_DIR/libs-gui"
fi
git -C "$SOURCES_DIR/libs-gui" fetch --tags origin
git -C "$SOURCES_DIR/libs-gui" checkout --detach "7892137bdedd007eba8425f766e41481ddb4fda6"

if [ ! -d "$SOURCES_DIR/libs-back/.git" ]; then
  git clone "https://github.com/gnustep/libs-back.git" "$SOURCES_DIR/libs-back"
fi
git -C "$SOURCES_DIR/libs-back" fetch --tags origin
git -C "$SOURCES_DIR/libs-back" checkout --detach "bf3b3ced525f08415a20d109f05be1f91492414c"

case "$HOST_OS" in
  linux)
    export MAKE=gmake
    ;;
  openbsd)
    export MAKE=gmake
    export PKG_CONFIG=pkg-config
    export AUTOCONF_VERSION=${AUTOCONF_VERSION:-2.72}
    export AUTOMAKE_VERSION=${AUTOMAKE_VERSION:-1.17}
    ;;
esac

cd "$SOURCES_DIR/libobjc2"
rm -rf build
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_OBJC_COMPILER=clang \
  -DCMAKE_OBJCXX_COMPILER=clang++ \
  -DGNUSTEP_INSTALL_TYPE=NONE \
  -DEMBEDDED_BLOCKS_RUNTIME=ON
cmake --build build -j"$JOBS"
cmake --install build

cd "$SOURCES_DIR/libdispatch"
rm -rf build
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_PREFIX_PATH="$PREFIX" \
  -DBUILD_TESTING=OFF
cmake --build build -j"$JOBS"
cmake --install build

export CC=clang
export CXX=clang++
export OBJC=clang
export OBJCXX=clang++
export PATH="$PREFIX/System/Tools:$PREFIX/bin:$PATH"
export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib64:${LD_LIBRARY_PATH:-}"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib64/pkgconfig:${PKG_CONFIG_PATH:-}"
export CPPFLAGS="-I$PREFIX/include ${CPPFLAGS:-}"
export CFLAGS="-I$PREFIX/include ${CFLAGS:-}"
export CXXFLAGS="-I$PREFIX/include ${CXXFLAGS:-}"
export OBJCFLAGS="-I$PREFIX/include ${OBJCFLAGS:-}"
export OBJCXXFLAGS="-I$PREFIX/include ${OBJCXXFLAGS:-}"
export LDFLAGS="-L$PREFIX/lib -L$PREFIX/lib64 ${LDFLAGS:-}"

cd "$SOURCES_DIR/tools-make"
./configure --prefix="$PREFIX" --with-layout=gnustep --enable-native-objc-exceptions --enable-objc-arc --with-library-combo=ng-gnu-gnu
"${MAKE:-make}" -j"$JOBS"
"${MAKE:-make}" install

export GNUSTEP_SYSTEM_ROOT="$PREFIX/System"
export GNUSTEP_LOCAL_ROOT="$PREFIX/Local"
export GNUSTEP_NETWORK_ROOT="$PREFIX/Network"
export GNUSTEP_MAKEFILES="$PREFIX/System/Library/Makefiles"
set +u
. "$GNUSTEP_MAKEFILES/GNUstep.sh"
set -u
unset GNUSTEP_SYSTEM_ROOT GNUSTEP_LOCAL_ROOT GNUSTEP_NETWORK_ROOT

# Expose the managed Objective-C runtime headers through the GNUstep header domain.
ln -sfn "$PREFIX/include/objc" "$PREFIX/Local/Library/Headers/objc"
cp -f "$PREFIX/include/Block.h" "$PREFIX/Local/Library/Headers/Block.h"
cp -f "$PREFIX/include/Block_private.h" "$PREFIX/Local/Library/Headers/Block_private.h"

for lib in libs-base libs-corebase libs-gui libs-back; do
  cd "$SOURCES_DIR/$lib"
  "${MAKE:-make}" distclean >/dev/null 2>&1 || true
  ./configure --prefix="$PREFIX"
  "${MAKE:-make}" -j"$JOBS"
  "${MAKE:-make}" install
done

printf "%s\n" "$HOST_OS managed toolchain build completed at $PREFIX"

