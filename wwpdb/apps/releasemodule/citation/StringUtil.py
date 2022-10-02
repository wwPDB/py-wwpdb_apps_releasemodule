##
# File:  StringUtil.py
# Date:  10-Jul-2013
# Updates:
##
"""
Find similarity between two strings.

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2013 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"


def calLevenshteinDistance(first, second):
    """ Find the Levenshtein distance between two strings.
    """
    if len(first) > len(second):
        first, second = second, first
    if len(second) == 0:
        return len(first)
    first_length = len(first) + 1
    second_length = len(second) + 1
    distance_matrix = [[0] * second_length for x in range(first_length)]
    for i in range(first_length):
        distance_matrix[i][0] = i
    for j in range(second_length):
        distance_matrix[0][j] = j
    for i in range(1, first_length):
        for j in range(1, second_length):
            deletion = distance_matrix[i - 1][j] + 1
            insertion = distance_matrix[i][j - 1] + 1
            substitution = distance_matrix[i - 1][j - 1]
            if first[i - 1] != second[j - 1]:
                substitution += 1
            distance_matrix[i][j] = min(insertion, deletion, substitution)
    return distance_matrix[first_length - 1][second_length - 1]


def levenshtein(seq1, seq2):
    oneago = None
    thisrow = list(range(1, len(seq2) + 1)) + [0]
    for x in range(len(seq1)):
        _twoago, oneago, thisrow = oneago, thisrow, [0] * len(seq2) + [x + 1]  # noqa: F841
        for y in range(len(seq2)):
            delcost = oneago[y] + 1
            addcost = thisrow[y - 1] + 1
            subcost = oneago[y - 1] + (seq1[x] != seq2[y])
            thisrow[y] = min(delcost, addcost, subcost)
    return thisrow[len(seq2) - 1]


def calStringSimilarity(first, second):
    """ Find similarity (0-1 scale) between two strings.
    """
    if not first or not second:
        return 0.0
    #
    s1 = first.lower()
    s2 = second.lower()
    length = len(s1)
    if len(s2) > length:
        length = len(s2)
    if length == 0:
        return 0.0
    #
    dist = calLevenshteinDistance(s1, s2)
    # dist = levenshtein(s1, s2)
    sim = 1.0 - float(dist) / float(length)
    #
    return sim
