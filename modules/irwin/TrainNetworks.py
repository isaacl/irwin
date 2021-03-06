import threading

from modules.irwin.updatePlayerEngineStatus import updatePlayerEngineStatus
from modules.irwin.writeCSV import writeClassifiedMovesCSV, writeClassifiedMoveChunksCSV, writeClassifiedPVsCSV
from modules.irwin.MoveAssessment import MoveAssessment
from modules.irwin.ChunkAssessment import ChunkAssessment
from modules.irwin.PVAssessment import PVAssessment

class TrainNetworks(threading.Thread):
  def __init__(self, api, playerAnalysisDB):
    threading.Thread.__init__(self)
    self.api = api
    self.playerAnalysisDB = playerAnalysisDB

  def run(self):
    updatePlayerEngineStatus(self.api, self.playerAnalysisDB)
    sortedUsers = self.playerAnalysisDB.balancedSorted()
    self.classifyMoves(sortedUsers)
    self.classifyMoveChunks(sortedUsers)
    self.classifyPVs(sortedUsers)
    MoveAssessment.learn()
    ChunkAssessment.learn()
    PVAssessment.learn()

  def classifyMoves(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVMoves()) for playerAnalysis in playerAnalyses]
    writeClassifiedMovesCSV(entries)

  def classifyMoveChunks(self, playerAnalyses):
    entries = []
    [entries.extend(playerAnalysis.CSVChunks()) for playerAnalysis in playerAnalyses]
    writeClassifiedMoveChunksCSV(entries)

  def classifyPVs(self, playerAnalyses):
    entries = []
    [entries.append(playerAnalysis.CSVPVs()) for playerAnalysis in playerAnalyses]
    writeClassifiedPVsCSV(entries)