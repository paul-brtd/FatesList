package main

import (
	"dragon/common"
	"dragon/server"
	"os"
	"os/exec"
	"strings"

	log "github.com/sirupsen/logrus"
)

func main() {
	lvl, ok := os.LookupEnv("LOG_LEVEL")
	if !ok {
		lvl = "debug"
	}
	ll, err := log.ParseLevel(lvl)
	if err != nil {
		ll = log.DebugLevel
	}
	log.SetLevel(ll)

	if common.CliCmd == "dragon.server" {
		server.DragonServer()
		os.Exit(0)
	} else {
		cmdFunc := strings.Replace(common.CliCmd, ".", "_", -1)
		pyCmd := "from modules.core._manage import " + cmdFunc + "; " + cmdFunc + "()"
		log.Info("Running " + common.PythonPath + " -c '" + pyCmd + "'")
		os.Setenv("MAIN_TOKEN", common.MainBotToken)
		os.Setenv("CLIENT_SECRET", common.ClientSecret)
		if os.Getenv("PYLOG_LEVEL") != "debug" {
			os.Setenv("LOGURU_LEVEL", "INFO")
		}
		devserver := exec.Command(common.PythonPath, "-c", pyCmd)
		devserver.Dir = common.RootPath
		devserver.Env = os.Environ()
		devserver.Stdout = os.Stdout
		devserver.Stderr = os.Stderr
		devserver.Run()
	}
}
