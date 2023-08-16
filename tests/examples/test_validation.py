#!/usr/bin/env python3

# Portions of this file contributed by NIST are governed by the following
# statement:
#
# This software was developed at the National Institute of Standards
# and Technology by employees of the Federal Government in the course
# of their official duties. Pursuant to Title 17 Section 105 of the
# United States Code, this software is not subject to copyright
# protection within the United States. NIST assumes no responsibility
# whatsoever for its use by other parties, and makes no guarantees,
# expressed or implied, about its quality, reliability, or any other
# characteristic.
#
# We would appreciate acknowledgement if the software is used.


"""
Tests in this file confirm that the JSON-LD files with "PASS" in the
name pass SHACL validation, and JSON-LD files with "XFAIL" in the name
not only fail SHACL validation, but also report a set ofproperties used
in their JSON-LD that triggered SHACL validation errors.

This test was written to be called with the pytest framework, expecting
the only functions to be called to be named "test_*".
"""

import logging
from typing import Any, Optional, Set, Tuple

from rdflib import SH, Graph, Literal, URIRef
from rdflib.plugins.sparql.processor import prepareQuery
from rdflib.query import ResultRow
from rdflib.term import IdentifiedNode

NS_SH = SH

NSDICT = {"sh": NS_SH}


def load_validation_graph(filename: str, expected_conformance: bool) -> Graph:
    g = Graph()
    g.parse(filename, format="turtle")
    g.namespace_manager.bind("sh", NS_SH)

    query = prepareQuery(
        """\
SELECT ?lConforms
WHERE {
  ?nReport
    a sh:ValidationReport ;
    sh:conforms ?lConforms ;
    .
}
""",
        initNs=NSDICT,
    )

    computed_conformance = None
    for result in g.query(query):
        assert isinstance(result, ResultRow)
        assert isinstance(result[0], Literal)
        l_conforms = result[0]
        computed_conformance = bool(l_conforms)
    assert expected_conformance == computed_conformance
    return g


def confirm_validation_results(
    filename: str,
    expected_conformance: bool,
    *args: Any,
    expected_focus_node_severities: Optional[Set[Tuple[str, str]]] = None,
    expected_result_paths: Optional[Set[str]] = None,
    expected_source_shapes: Optional[Set[str]] = None
) -> None:
    """
    The expected-sets are sets where names are known.

    Blank nodes are omitted, and should be tested with a different set.
    """
    g = load_validation_graph(filename, expected_conformance)

    computed_focus_node_severities = set()
    computed_result_paths = set()
    computed_source_shapes = set()

    query = prepareQuery(
        """\
SELECT DISTINCT ?nFocusNode ?nResultPath ?nSeverity ?nSourceShape
WHERE {
  ?nReport
    a sh:ValidationReport ;
    sh:result ?nValidationResult ;
    .

  ?nValidationResult
    a sh:ValidationResult ;
    sh:focusNode ?nFocusNode ;
    sh:resultSeverity ?nSeverity ;
    sh:sourceShape ?nSourceShape ;
    .

  # sh:not violations do not have a sh:resultPath.
  OPTIONAL {
  ?nValidationResult
    sh:resultPath ?nResultPath ;
    .
  }
}
""",
        initNs=NSDICT,
    )

    for result in g.query(query):
        assert isinstance(result, ResultRow)
        assert isinstance(result[0], IdentifiedNode)
        assert result[1] is None or isinstance(result[1], IdentifiedNode)
        assert isinstance(result[2], URIRef)
        assert isinstance(result[3], IdentifiedNode)
        (n_focus_node, n_result_path, n_severity, n_source_shape) = result

        computed_focus_node_severities.add((str(n_focus_node), str(n_severity)))

        if isinstance(n_result_path, URIRef):
            computed_result_paths.add(str(n_result_path))

        if isinstance(n_source_shape, URIRef):
            computed_source_shapes.add(str(n_source_shape))

    if expected_focus_node_severities is not None:
        try:
            assert expected_focus_node_severities == computed_focus_node_severities
        except AssertionError:
            logging.error(
                "Please review %s and its associated .json file to identify the ground truth validation error mismatch pertaining to named focus nodes noted in this function.",
                filename,
            )
            raise

    if expected_result_paths is not None:
        try:
            assert expected_result_paths == computed_result_paths
        except AssertionError:
            logging.error(
                "Please review %s and its associated .json file to identify the ground truth validation error mismatch pertaining to data properties noted in this function.",
                filename,
            )
            raise

    if expected_source_shapes is not None:
        try:
            assert expected_source_shapes == computed_source_shapes
        except AssertionError:
            logging.error(
                "Please review %s and its associated .json file to identify the ground truth validation error mismatch pertaining to named source shapes noted in this function.",
                filename,
            )
            raise


def test_owl_axiom_PASS() -> None:
    confirm_validation_results(
        "owl_axiom_PASS_validation.ttl", True, expected_focus_node_severities=set()
    )


def test_owl_axiom_XFAIL() -> None:
    confirm_validation_results(
        "owl_axiom_XFAIL_validation.ttl",
        False,
        expected_focus_node_severities={
            ("http://example.org/kb/axiom-1", str(NS_SH.Violation)),
        },
    )


def test_owl_properties_PASS() -> None:
    confirm_validation_results(
        "owl_properties_PASS_validation.ttl", True, expected_focus_node_severities=set()
    )


def test_owl_properties_XFAIL() -> None:
    confirm_validation_results(
        "owl_properties_XFAIL_validation.ttl",
        False,
        expected_focus_node_severities={
            ("http://example.org/kb/cross-property-ad", str(NS_SH.Violation)),
            ("http://example.org/kb/cross-property-ao", str(NS_SH.Violation)),
            ("http://example.org/kb/cross-property-do", str(NS_SH.Violation)),
        },
    )


def test_rdf_list_PASS() -> None:
    confirm_validation_results(
        "rdf_list_PASS_validation.ttl", True, expected_focus_node_severities=set()
    )


def test_rdf_list_XFAIL() -> None:
    confirm_validation_results("rdf_list_XFAIL_validation.ttl", False)
