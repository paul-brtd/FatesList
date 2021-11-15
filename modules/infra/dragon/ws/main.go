// Based on https://github.com/gorilla/websocket/blob/master/examples/chat/main.go

// Copyright 2013 The Gorilla WebSocket Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package ws

import (
	"net"
	"net/http"

	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var addr = ":10293"

func StartWS(db *pgxpool.Pool, rdb *redis.Client) {
	hub := newHub(db, rdb)
	go hub.run()
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		serveWs(hub, w, r)
	})

	listener, err := net.Listen("unix", "/home/meow/fatesws.sock")
	if err != nil {
		log.Fatal("could not start listening: ", err)
		return
	}

	err = http.Serve(listener, nil)

	if err != nil {
		log.Error("Could not start websocket: ", err)
	}
}
