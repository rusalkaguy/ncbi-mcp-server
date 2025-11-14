"""NCBI MCP Server - Main server implementation."""

import json
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ncbi_mcp_server.ncbi_client import NCBIClient, NCBIConfig


class ServerContext(BaseModel):
    """Server context with NCBI client."""

    model_config = {"arbitrary_types_allowed": True}

    ncbi_client: NCBIClient


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage server lifecycle with NCBI client."""
    # Initialize NCBI client
    config = NCBIConfig(
        api_key=os.getenv("NCBI_API_KEY"),
        email=os.getenv("NCBI_EMAIL", "user@example.com"),
    )

    async with NCBIClient(config) as ncbi_client:
        yield ServerContext(ncbi_client=ncbi_client)


# Initialize MCP server
mcp = FastMCP(
    "NCBI MCP Server",
    dependencies=[
        "httpx>=0.25.0",
        "biopython>=1.81",
        "xmltodict>=0.13.0",
        "pydantic>=2.0.0",
    ],
    lifespan=server_lifespan,
)


@mcp.tool()
async def search_ncbi(
    database: str,
    query: str,
    max_results: int = 20,
    start_index: int = 0,
    sort_order: Optional[str] = None,
) -> str:
    """
    Search NCBI database using E-utilities.

    Args:
        database: NCBI database to search (e.g., 'pubmed', 'protein', 'nucleotide')
        query: Search query string
        max_results: Maximum number of results to return (default: 20)
        start_index: Starting index for results (default: 0)
        sort_order: Sort order for results (optional)

    Returns:
        JSON string with search results including IDs and metadata
    """
    ctx = mcp.get_context()
    ncbi_client = ctx.request_context.lifespan_context.ncbi_client

    try:
        result = await ncbi_client.search(
            database=database,
            query=query,
            retmax=max_results,
            retstart=start_index,
            sort=sort_order,
        )

        return json.dumps(
            {
                "success": True,
                "database": database,
                "query": query,
                "total_count": result.count,
                "returned_count": len(result.ids),
                "start_index": result.retstart,
                "ids": result.ids,
                "query_translation": result.query_translation,
                "web_env": result.web_env,
                "query_key": result.query_key,
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": str(e), "database": database, "query": query},
            indent=2,
        )


@mcp.tool()
async def fetch_records(
    database: str, ids: List[str], return_type: str = "xml", return_mode: str = "xml"
) -> str:
    """
    Fetch records from NCBI database using E-utilities.

    Args:
        database: NCBI database name
        ids: List of record IDs to fetch
        return_type: Format of returned data (xml, fasta, gb, etc.)
        return_mode: Mode of returned data (xml, text)

    Returns:
        Raw data from NCBI in requested format
    """
    ctx = mcp.get_context()
    ncbi_client = ctx.request_context.lifespan_context.ncbi_client

    try:
        result = await ncbi_client.fetch(
            database=database, ids=ids, rettype=return_type, retmode=return_mode
        )

        return result

    except Exception as e:
        return json.dumps(
            {"success": False, "error": str(e), "database": database, "ids": ids},
            indent=2,
        )


@mcp.tool()
async def summarize_records(database: str, ids: List[str]) -> str:
    """
    Get document summaries for NCBI records using E-utilities.

    Args:
        database: NCBI database name
        ids: List of record IDs to summarize

    Returns:
        JSON string with record summaries including titles, authors, etc.
    """
    ctx = mcp.get_context()
    ncbi_client = ctx.request_context.lifespan_context.ncbi_client

    try:
        summaries = await ncbi_client.summary(database=database, ids=ids)

        summary_data = []
        for summary in summaries:
            summary_data.append(
                {
                    "uid": summary.uid,
                    "title": summary.title,
                    "authors": summary.authors,
                    "journal": summary.journal,
                    "pub_date": summary.pub_date,
                    "doi": summary.doi,
                    "pmid": summary.pmid,
                }
            )

        return json.dumps(
            {"success": True, "database": database, "summaries": summary_data}, indent=2
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": str(e), "database": database, "ids": ids},
            indent=2,
        )


@mcp.tool()
async def find_related_records(
    source_database: str, target_database: str, ids: List[str]
) -> str:
    """
    Find related records between NCBI databases using E-utilities.

    Args:
        source_database: Source NCBI database
        target_database: Target NCBI database to find related records
        ids: List of source record IDs

    Returns:
        JSON string with related record IDs
    """
    ctx = mcp.get_context()
    ncbi_client = ctx.request_context.lifespan_context.ncbi_client

    try:
        related_ids = await ncbi_client.link(
            database_from=source_database, database_to=target_database, ids=ids
        )

        return json.dumps(
            {
                "success": True,
                "source_database": source_database,
                "target_database": target_database,
                "source_ids": ids,
                "related_ids": related_ids,
                "related_count": len(related_ids),
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "source_database": source_database,
                "target_database": target_database,
                "ids": ids,
            },
            indent=2,
        )


@mcp.tool()
async def get_database_info(database: Optional[str] = None) -> str:
    """
    Get information about NCBI databases using E-utilities.

    Args:
        database: Specific database name (optional - if not provided, lists all databases)

    Returns:
        JSON string with database information
    """
    ctx = mcp.get_context()
    ncbi_client = ctx.request_context.lifespan_context.ncbi_client

    try:
        info = await ncbi_client.info(database=database)

        return json.dumps(
            {"success": True, "database": database, "info": info}, indent=2
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": str(e), "database": database}, indent=2
        )


@mcp.tool()
async def list_databases() -> str:
    """
    Get list of available NCBI databases.

    Returns:
        JSON string with list of available databases
    """
    ctx = mcp.get_context()
    ncbi_client = ctx.request_context.lifespan_context.ncbi_client

    try:
        databases = await ncbi_client.get_databases()

        return json.dumps(
            {"success": True, "databases": databases, "count": len(databases)}, indent=2
        )

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
async def blast_search(
    program: str,
    database: str,
    sequence: str,
    expect_value: float = 10.0,
    word_size: Optional[int] = None,
    matrix: Optional[str] = None,
    gap_costs: Optional[str] = None,
    output_fmt: str = "full",
    megablast: bool = None,
) -> str:
    """
    Perform BLAST search using NCBI BLAST.

    Args:
        program: BLAST program (blastn, blastp, blastx, tblastn, tblastx)
        database: BLAST database (nr, nt, refseq_protein, etc.)
        sequence: Query sequence in FASTA format or raw sequence
        expect_value: E-value threshold (default: 10.0)
        word_size: Word size for BLAST search (optional)
        matrix: Scoring matrix (optional, e.g., BLOSUM62)
        gap_costs: Gap costs (optional, e.g., "11 1")
        output_fmt: Output format ("full" includes alignment strings, "summary" omits them)
        megablast: Whether to use megablast (only for blastn; default: None, True to enable megablast)
    Returns:
        JSON string with BLAST results
    """
    ctx = mcp.get_context()
    ncbi_client = ctx.request_context.lifespan_context.ncbi_client

    try:
        if output_fmt not in {"full", "summary"}:
            raise ValueError("Invalid output_fmt value. Must be 'full' or 'summary'.")

        result = await ncbi_client.blast_search(
            program=program,
            database=database,
            sequence=sequence,
            expect=expect_value,
            word_size=word_size,
            matrix=matrix,
            gapcosts=gap_costs,
            output_fmt=output_fmt,
            megablast=megablast,
        )

        return json.dumps(
            {
                "success": True,
                "program": program,
                "database": database,
                "rid": result.rid,
                "status": result.status,
                "results": result.results,
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "program": program,
                "database": database,
            },
            indent=2,
        )


@mcp.resource("ncbi://databases")
async def get_databases_resource() -> str:
    """Resource providing list of available NCBI databases."""
    ctx = mcp.get_context()
    ncbi_client = ctx.request_context.lifespan_context.ncbi_client

    try:
        databases = await ncbi_client.get_databases()

        # Create a formatted list of databases with descriptions
        database_info = {
            "pubmed": "PubMed biomedical literature database",
            "protein": "Protein sequence database",
            "nucleotide": "Nucleotide sequence database",
            "nuccore": "Nucleotide collection (GenBank+EMBL+DDBJ+PDB+RefSeq)",
            "gene": "Gene-centered information",
            "genome": "Genome sequencing projects",
            "assembly": "Genome assemblies",
            "bioproject": "BioProject metadata",
            "biosample": "BioSample metadata",
            "sra": "Sequence Read Archive",
            "taxonomy": "Taxonomic information",
            "pmc": "PubMed Central full-text articles",
            "books": "NCBI Bookshelf",
            "mesh": "Medical Subject Headings",
            "snp": "Single Nucleotide Polymorphism",
            "clinvar": "Clinical significance of genomic variation",
        }

        formatted_databases = []
        for db in databases:
            description = database_info.get(db, "NCBI database")
            formatted_databases.append(f"- **{db}**: {description}")

        return f"""# Available NCBI Databases

Total databases: {len(databases)}

{chr(10).join(formatted_databases)}

## Usage
Use these database names with the search_ncbi, fetch_records, and other tools.
"""

    except Exception as e:
        return f"Error retrieving databases: {str(e)}"


@mcp.resource("ncbi://blast-programs")
async def get_blast_programs_resource() -> str:
    """Resource providing information about BLAST programs."""
    return """# BLAST Programs Available

## Basic BLAST Programs

- **blastn**: Nucleotide-nucleotide BLAST
  - Compares nucleotide query sequences against nucleotide sequence databases
  - Best for DNA/RNA sequences

- **blastp**: Protein-protein BLAST  
  - Compares amino acid query sequences against protein sequence databases
  - Best for protein sequences

- **blastx**: Nucleotide-protein BLAST
  - Compares nucleotide query sequences translated in all frames against protein databases
  - Useful for finding protein matches for DNA sequences

- **tblastn**: Protein-nucleotide BLAST
  - Compares protein query sequences against nucleotide databases translated in all frames
  - Useful for finding DNA matches for protein sequences

- **tblastx**: Translated nucleotide-nucleotide BLAST
  - Compares nucleotide query sequences translated in all frames against nucleotide databases also translated in all frames
  - Most sensitive but slowest option

## Common BLAST Databases

### Nucleotide Databases
- **nt**: Non-redundant nucleotide collection
- **refseq_rna**: RefSeq RNA sequences  
- **16S_ribosomal_RNA**: 16S ribosomal RNA sequences

### Protein Databases  
- **nr**: Non-redundant protein sequences
- **refseq_protein**: RefSeq protein sequences
- **pdb**: Protein Data Bank sequences
- **swissprot**: SwissProt protein sequences

## Usage Example
```
blast_search(
    program="blastn",
    database="nt", 
    sequence="ATCGATCGATCG",
    expect_value=0.001
)
```
"""


def main():
    """Main entry point for the server."""
    mcp.run()


if __name__ == "__main__":
    main()
