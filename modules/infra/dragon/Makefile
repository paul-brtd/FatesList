PACKAGE:=dragon/common
VERSION:=$(shell git describe --tags --always --abbrev=0 --match='v[0-9]*.[0-9]*.[0-9]*' 2> /dev/null | sed 's/^.//')
COMMIT_HASH:=$(shell git rev-parse --short HEAD)
BUILD_TIMESTAMP:=$(shell date '+%Y-%m-%dT%H:%M:%S')

LDFLAGS=-X ${PACKAGE}.Version=${VERSION} \
  -X ${PACKAGE}.CommitHash=${COMMIT_HASH} \
  -X ${PACKAGE}.BuildTime=${BUILD_TIMESTAMP} \

all:
	#go build -v -ldflags="${LDFLAGS}" -o dragon-dyn
	CGO_ENABLED=0 go build -v -a -ldflags="${LDFLAGS}"
install:
	cp dragon /usr/local/bin
