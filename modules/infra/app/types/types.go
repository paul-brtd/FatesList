package types

type BaseUser struct {
	Username string    `json:"username"`
	ID       string    `json:"id"`
	Avatar   string    `json:"avatar"`
	Disc     string    `json:"disc"`
	Status   BotStatus `json:"status"`
	Bot      bool      `json:"bot"`
}

type BotStatus int

const (
	BotStatusUnknown BotStatus = 0
	BotStatusOnline  BotStatus = 1
	BotStatusOffline BotStatus = 2
	BotStatusIdle    BotStatus = 3
	BotStatusDnd     BotStatus = 4
)

type BotState int

// TODO
//const (
//	BotStateApproved BotState = 0
//)

type BotPartial struct {
	Description string   `json:"description"`
	GuildCount  int      `json:"guild_count"`
	Banner      string   `json:"banner,omitempty"`
	State       BotState `json:"state"`
	NSFW        bool     `json:"nsfw"`
	Votes       int      `json:"votes"`
	User        BaseUser `json:"user"`
}

type Index struct {
	TopVoted      []BotPartial `json:"top_voted"`
	CertifiedBots []BotPartial `json:"certified_bots"`
	NewBots       []BotPartial `json:"new_bots"`
}
