package common

import (
	"io/ioutil"
	"net/http"
	"strings"

	log "github.com/sirupsen/logrus"
)

func RenderPossibleLink(link string) (res string) {
	// Donverts links (right now only pastebin) to text
	var origData = link
	if !strings.HasPrefix(link, "https://") && !strings.HasPrefix(link, "http://") && !strings.HasPrefix(link, "www.") {
		return origData
	}
	link = strings.Replace(link, "https://", "", 1)
	link = strings.Replace(link, "http://", "", 1)
	link = strings.Replace(link, "www.", "", 1)

	// Pastebin
	if strings.HasPrefix(link, "pastebin.com") {
		pasteId := strings.Replace(strings.Replace(link, "pastebin.com", "", 1), "/", "", -1)
		rawPasteUrl := "https://pastebin.com/raw/" + pasteId
		resp, err := http.Get(rawPasteUrl)
		if err != nil {
			log.Error(err)
			return origData
		}
		body, err := ioutil.ReadAll(resp.Body)
		if err != nil {
			log.Error(err)
			return origData
		}
		return string(body)
	}
	return origData
}
