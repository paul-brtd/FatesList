package main

import (
	"app/types"
	"bytes"
	"image"
	"net/http"
	"time"

	"gioui.org/layout"
	"gioui.org/op/paint"
	"gioui.org/widget"
	"gioui.org/widget/material"
)

var imgCache map[string]image.Image = make(map[string]image.Image)

func renderIndexPage(t string, gtx layout.Context, index types.Index, th *material.Theme) layout.Dimensions {
	if t != "bots" && t != "servers" {
		panic("Invalid index page type")
	}

	layoutDat := layout.Flex{
		Axis:    layout.Vertical,
		Spacing: layout.SpaceStart,
	}

	var flexChild []layout.FlexChild

	flexChild = append(flexChild, layout.Rigid(
		func(gtx layout.Context) layout.Dimensions {
			h1 := material.H1(th, "Fates List")
			return h1.Layout(gtx)
		},
	))

	for _, botDat := range index.TopVoted {
		bot := botDat

		if bot.User.Avatar == "" {
			bot.User.Avatar = "/static/botlisticon.webp"
		}

		widgets := []layout.FlexChild{
			layout.Rigid(
				func(gtx layout.Context) layout.Dimensions {
					stack := layout.Stack{Alignment: layout.SW}
					username := material.H2(th, bot.User.Username)
					description := material.Body1(th, bot.Description)

					avatar := widget.Image{
						Src: paint.NewImageOp(image.NewRGBA(image.Rectangle{image.Point{0, 0}, image.Point{50, 50}})),
					}
					stackD := stack.Layout(gtx,
						layout.Expanded(
							func(gtx layout.Context) layout.Dimensions {
								return avatar.Layout(gtx)
							},
						),
						layout.Expanded(
							func(gtx layout.Context) layout.Dimensions {
								return username.Layout(gtx)
							},
						),
						layout.Stacked(
							func(gtx layout.Context) layout.Dimensions {
								return description.Layout(gtx)
							},
						),
					)
					return stackD
				},
			),
		}
		flexChild = append(flexChild, widgets...)
	}

	return layoutDat.Layout(gtx, flexChild...)
}

func getImage(path string, id string) {
	defer recoverImg(id)

	if _, ok := imgCache[id]; ok {
		return
	}

	avatarBytes, err := request(http.Client{Timeout: 15 * time.Second}, "GET", path, map[string]string{}, map[string]interface{}{})
	if err != nil {
		avatarBytes = []byte{}
	}

	var img image.Image

	img, _, err = image.Decode(bytes.NewReader(avatarBytes))

	if err != nil {
		img = image.NewRGBA(image.Rectangle{image.Point{0, 0}, image.Point{50, 50}})
	}
	imgCache[id] = img
}

func recoverImg(id string) {
	if r := recover(); r != nil {
		imgCache[id] = image.NewRGBA(image.Rectangle{image.Point{0, 0}, image.Point{50, 50}})
	}
}
