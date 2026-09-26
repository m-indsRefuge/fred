from fred.brain.memory.contracts import Visibility
from fred.brain.retrieval.contracts import RetrievalCandidate


def assign_visibility(candidates: list[RetrievalCandidate]) -> None:
    for index, candidate in enumerate(candidates):
        if index < 3:
            candidate.visibility = Visibility.FULL
        elif index < 8:
            candidate.visibility = Visibility.SUMMARY
        else:
            candidate.visibility = Visibility.SIGNAL

