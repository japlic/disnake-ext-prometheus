import logging
from prometheus_client import start_http_server, Counter, Gauge
from disnake.ext import commands, tasks
from disnake import Interaction, InteractionType, AutoShardedClient
from disnake.ext.commands import Bot
from logging import Handler
from prometheus_client import Counter

LOGGING_COUNTER = Counter("logging", "Log entries", ["logger", "level"])


class PrometheusLoggingHandler(Handler):
    """
    A logging handler that adds logging metrics to prometheus
    """

    def emit(self, record):
        LOGGING_COUNTER.labels(record.name, record.levelname).inc()

log = logging.getLogger("prometheus")

METRIC_PREFIX = "discord_"

CONNECTION_GAUGE = Gauge(
    METRIC_PREFIX + "connected",
    "Determines if the bot is connected to Discord",
    ["shard"],
)
LATENCY_GAUGE = Gauge(
    METRIC_PREFIX + "latency",
    "latency to Discord",
    ["shard"],
    unit="seconds",
)
ON_INTERACTION_COUNTER = Counter(
    METRIC_PREFIX + "event_on_interaction",
    "Amount of interactions called by users",
    ["shard", "interaction", "command"],
)
ON_COMMAND_COUNTER = Counter(
    METRIC_PREFIX + "event_on_command",
    "Amount of commands called by users",
    ["shard", "command"],
)
GUILD_GAUGE = Gauge(
    METRIC_PREFIX + "stat_total_guilds", "Amount of guild this bot is a member of"
)
CHANNEL_GAUGE = Gauge(
    METRIC_PREFIX + "stat_total_channels",
    "Amount of channels this bot has access to",
)
USER_GAUGE = Gauge(
    METRIC_PREFIX + "stat_total_users", "Amount of users this bot can see"
)
COMMANDS_GAUGE = Gauge(METRIC_PREFIX + "stat_total_commands", "Amount of commands")


class PrometheusCog(commands.Cog):
    def __init__(self, bot: Bot, port: int = 9000):
        self.bot = bot
        self.port = port
        self.started = False
        self.latency_loop.start()

    def init_gauges(self):
        log.debug("Initializing gauges")
        GUILD_GAUGE.set(len(self.bot.guilds))
        CHANNEL_GAUGE.set(len(set(self.bot.get_all_channels())))
        USER_GAUGE.set(len(set(self.bot.get_all_members())))
        COMMANDS_GAUGE.set(len(self.get_all_commands()))

    def get_all_commands(self):
        return [*self.bot.walk_commands(), *self.bot.walk_commands()]

    def start_prometheus(self):
        log.debug(f"Starting Prometheus Server on port {self.port}")
        start_http_server(self.port, addr="0.0.0.0")
        self.started = True

    @tasks.loop(seconds=5)
    async def latency_loop(self):
        if isinstance(self.bot, AutoShardedClient):
            for shard, latency in self.bot.latencies:
                LATENCY_GAUGE.labels(shard).set(latency)
        else:
            LATENCY_GAUGE.labels(None).set(self.bot.latency)

    @commands.Cog.listener()
    async def on_ready(self):
        self.init_gauges()
        CONNECTION_GAUGE.labels(None).set(1)
        if not self.started:
            self.start_prometheus()

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        shard_id = ctx.guild.shard_id if ctx.guild else None
        ON_COMMAND_COUNTER.labels(shard_id, ctx.command.name).inc()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        shard_id = interaction.guild.shard_id if interaction.guild else None
        command_name = None

        if interaction.type == InteractionType.application_command and interaction.application_command:
            command_name = interaction.application_command.qualified_name

        ON_INTERACTION_COUNTER.labels(
            shard_id, interaction.type.name, command_name
        ).inc()

    @commands.Cog.listener()
    async def on_connect(self):
        CONNECTION_GAUGE.labels(None).set(1)

    @commands.Cog.listener()
    async def on_resumed(self):
        CONNECTION_GAUGE.labels(None).set(1)

    @commands.Cog.listener()
    async def on_disconnect(self):
        CONNECTION_GAUGE.labels(None).set(0)

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        CONNECTION_GAUGE.labels(shard_id).set(1)

    @commands.Cog.listener()
    async def on_shard_connect(self, shard_id):
        CONNECTION_GAUGE.labels(shard_id).set(1)

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id):
        CONNECTION_GAUGE.labels(shard_id).set(1)

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id):
        CONNECTION_GAUGE.labels(shard_id).set(0)

    @commands.Cog.listener()
    async def on_guild_join(self, _):
        self.init_gauges()

    @commands.Cog.listener()
    async def on_guild_remove(self, _):
        self.init_gauges()

    @commands.Cog.listener()
    async def on_guild_channel_create(self, _):
        CHANNEL_GAUGE.inc()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, _):
        CHANNEL_GAUGE.dec()

    @commands.Cog.listener()
    async def on_member_join(self, _):
        USER_GAUGE.inc()

    @commands.Cog.listener()
    async def on_member_remove(self, _):
        USER_GAUGE.dec()

def setup(bot):
  bot.add_cog(PrometheusCog(bot))
    