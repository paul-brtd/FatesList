package server

import (
	"context"
	"dragon/admin"
	"dragon/common"
	"dragon/ipc"
	"dragon/serverlist"
	"dragon/ws"
	"os"
	"os/signal"
	"syscall"

	"github.com/bwmarrin/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var (
	db               *pgxpool.Pool
	discord          *discordgo.Session
	discordServerBot *discordgo.Session
	rdb              *redis.Client
	ctx              context.Context = context.Background()
)

func DragonServer() {
	db, err := pgxpool.Connect(ctx, "")
	if err != nil {
		panic(err)
	}

	discord, err = discordgo.New("Bot " + common.MainBotToken)
	if err != nil {
		panic(err)
	}

	discord.Identify.Intents = discordgo.IntentsGuilds | discordgo.IntentsGuildPresences | discordgo.IntentsGuildMembers | discordgo.IntentsDirectMessages | discordgo.IntentsGuildMessages | discordgo.IntentsGuildMembers
	discordServerBot, err = discordgo.New("Bot " + common.ServerBotToken)
	if err != nil {
		panic(err)
	}
	discordServerBot.Identify.Intents = discordgo.IntentsGuilds | discordgo.IntentsDirectMessages

	onReady := func(s *discordgo.Session, m *discordgo.Ready) {
		log.Info("Logged in as ", m.User.Username)
	}

	discord.AddHandler(onReady)
	discordServerBot.AddHandler(onReady)

	// Slash command handling
	iHandle := func(s *discordgo.Session, i *discordgo.InteractionCreate, bot int) {
		log.WithFields(log.Fields{
			"i": spew.Sdump(i.Interaction),
		}).Info("Going to handle interaction")
		if bot == 0 {
			admin.SlashHandler(
				ctx,
				s,
				rdb,
				db,
				i,
			)
		} else if bot == 1 {
			serverlist.SlashHandler(
				ctx,
				s,
				rdb,
				db,
				i,
			)
		}
	}

	discord.AddHandler(func(s *discordgo.Session, i *discordgo.InteractionCreate) { iHandle(s, i, 0) })
	discordServerBot.AddHandler(func(s *discordgo.Session, i *discordgo.InteractionCreate) { iHandle(s, i, 1) })

	err = discord.Open()
	if err != nil {
		panic(err)
	}
	err = discordServerBot.Open()
	if err != nil {
		panic(err)
	}

	go admin.SetupSlash(discord)
	go serverlist.SetupSlash(discordServerBot)

	rdb = redis.NewClient(&redis.Options{
		Addr:     "localhost:1001",
		Password: "",
		DB:       1,
	})

	// Delete socket file
	os.Remove("/home/meow/fatesws.sock")

	// Channel for signal handling
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs,
		syscall.SIGINT,
		syscall.SIGQUIT)

	// Start IPC code
	go ipc.StartIPC(db, discord, discordServerBot, rdb)
	go ws.StartWS(db, rdb)

	s := <-sigs
	log.Info("Going to exit gracefully due to signal", s, "\n")
	ipc.SignalHandle(s, rdb)

	// Close all connections
	db.Close()
	rdb.Close()
	discord.Close()
	discordServerBot.Close()

	os.Exit(0)
}
