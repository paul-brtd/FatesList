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

	"github.com/Fates-List/discordgo"
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

	// For now, if we don't get the guild members intent in the future, this will be replaced with approx guild count
	discordServerBot.Identify.Intents = discordgo.IntentsGuilds | discordgo.IntentsDirectMessages | discordgo.IntentsGuildMembers

	// Be prepared to remove this handler if we don't get priv intents
	memberHandler := func(s *discordgo.Session, m *discordgo.Member) {
		g, err := discordServerBot.State.Guild(m.GuildID)
		if err != nil {
			log.Error(err)
		}
		err2 := serverlist.AddRecacheGuild(ctx, db, g)
		if err2 != "" {
			log.Error(err2)
		}
	}

	discordServerBot.AddHandler(func(s *discordgo.Session, m *discordgo.GuildMemberAdd) { memberHandler(s, m.Member) })
	discordServerBot.AddHandler(func(s *discordgo.Session, m *discordgo.GuildMemberRemove) { memberHandler(s, m.Member) })
	// End of potentially dangerous (priv code)

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
	discordServerBot.AddHandler(func(s *discordgo.Session, gc *discordgo.GuildCreate) {
		log.Info("Adding guild " + gc.Guild.ID + " (" + gc.Guild.Name + ")")
		err := serverlist.AddRecacheGuild(ctx, db, gc.Guild)
		if err != "" {
			log.Error(err)
		}
	})

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
