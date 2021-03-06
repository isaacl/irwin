import argparse
import sys
import logging
from pprint import pprint
from modules.bcolors.bcolors import bcolors

from modules.core.Game import Game
from modules.core.PlayerAssessment import PlayerAssessmentBSONHandler, PlayerAssessment, PlayerAssessments
from modules.core.GameAnalysis import GameAnalysis
from modules.core.PlayerAnalysis import PlayerAnalysis

from modules.core.recentGames import recentGames

from modules.irwin.updatePlayerEngineStatus import isEngine

from Env import Env

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("token", metavar="TOKEN",
                    help="secret token for the lichess api")
parser.add_argument("learn", metavar="LEARN",
                    help="does this bot learn", nargs="?", type=int, default=1)
parser.add_argument("threads", metavar="THREADS", nargs="?", type=int, default=4,
                    help="number of engine threads")
parser.add_argument("memory", metavar="MEMORY", nargs="?", type=int, default=2048,
                    help="memory in MB to use for engine hashtables")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="substantially reduce the number of logged messages")
settings = parser.parse_args()

try:
  # Optionally fix colors on Windows and in journals if the colorama module
  # is available.
  import colorama
  wrapper = colorama.AnsiToWin32(sys.stdout)
  if wrapper.should_wrap():
    sys.stdout = wrapper.stream
except ImportError:
  pass

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)

env = Env(settings)
env.irwin.train()

while True:
  # Get player data
  userId = env.api.getPlayerId()
  playerData = env.api.getPlayerData(userId)

  # Filter games and assessments for relevant info
  try:
    pas = list([PlayerAssessmentBSONHandler.reads(pa) for pa in playerData['assessment']['playerAssessments']])
    playerAssessments = PlayerAssessments(pas)
    games = recentGames(playerAssessments, playerData['games'])
    playerAssessments = playerAssessments.addNulls(userId, games, playerData['games'])
  except KeyError:
    continue # if either of these don't gather any useful data, skip them

  # Write stuff to mongo
  env.playerAssessmentDB.lazyWriteMany(playerAssessments)
  env.gameDB.lazyWriteGames(games)

  # Pull everything from mongo that we have on the player
  playerAssessments = env.playerAssessmentDB.byUserId(userId)
  games = env.gameDB.byIds(playerAssessments.gameIds())
  gameAnalyses = env.gameAnalysisDB.byUserId(userId)

  logging.debug("Already Analysed: " + str(len(gameAnalyses.gameAnalyses)))

  for g in games.games:
    if playerAssessments.hasGameId(g.id):
      gameAnalyses.append(GameAnalysis(g, playerAssessments.byGameId(g.id), [], [], []))

  gameAnalyses.analyse(env.engine, env.infoHandler)
  env.gameAnalysisDB.lazyWriteGames(gameAnalyses)

  playerAnalysis = env.irwin.assessPlayer(PlayerAnalysis(
    id = userId,
    titled = 'titled' in playerData['assessment']['user'].keys(),
    engine = None,
    gamesPlayed = playerData['assessment']['user']['games'],
    closedReports = sum(int(r.get('processedBy', None) is not None) for r in playerData['history'] if r['type'] == 'report' and r['data']['reason'] == 'cheat'),
    gameAnalyses = gameAnalyses,
    PVAssessment = None))

  env.playerAnalysisDB.write(playerAnalysis)
  env.api.postReport(playerAnalysis.report())