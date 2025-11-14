"""NCBI MCP Server - Main server implementation."""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ncbi_mcp_server.ncbi_client import NCBIClient, NCBIConfig

# Configure logging
logger = logging.getLogger(__name__)


class ServerContext(BaseModel):
    """Server context with NCBI client."""

    model_config = {"arbitrary_types_allowed": True}

    ncbi_client: NCBIClient


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage server lifecycle with NCBI client."""
    logger.info("Starting NCBI MCP Server")
    
    # Initialize NCBI client
    config = NCBIConfig(
        api_key=os.getenv("NCBI_API_KEY"),
        email=os.getenv("NCBI_EMAIL", "user@example.com"),
    )
    
    logger.debug(f"NCBI Configuration: email={config.email}, has_api_key={bool(config.api_key)}")

    async with NCBIClient(config) as ncbi_client:
        logger.info("NCBI client initialized successfully")
        yield ServerContext(ncbi_client=ncbi_client)
    
    logger.info("NCBI MCP Server shutting down")


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

    logger.info(f"Searching NCBI database '{database}' with query: {query[:100]}")
    logger.debug(f"Search parameters: max_results={max_results}, start_index={start_index}, sort_order={sort_order}")
    
    try:
        result = await ncbi_client.search(
            database=database,
            query=query,
            retmax=max_results,
            retstart=start_index,
            sort=sort_order,
        )
        
        logger.info(f"Search completed: {len(result.ids)} results returned (total: {result.count})")

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
        logger.error(f"Search failed for database '{database}': {str(e)}", exc_info=True)
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

    logger.info(f"Fetching {len(ids)} records from database '{database}'")
    logger.debug(f"Fetch parameters: return_type={return_type}, return_mode={return_mode}")
    
    try:
        result = await ncbi_client.fetch(
            database=database, ids=ids, rettype=return_type, retmode=return_mode
        )
        
        logger.info(f"Successfully fetched records from '{database}'")
        return result

    except Exception as e:
        logger.error(f"Fetch failed for database '{database}': {str(e)}", exc_info=True)
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

    logger.info(f"Retrieving summaries for {len(ids)} records from database '{database}'")
    
    try:
        summaries = await ncbi_client.summary(database=database, ids=ids)
        logger.info(f"Successfully retrieved {len(summaries)} summaries")

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
        logger.error(f"Summary retrieval failed for database '{database}': {str(e)}", exc_info=True)
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

    logger.info(f"Finding related records from '{source_database}' to '{target_database}'")
    logger.debug(f"Source IDs: {ids}")
    
    try:
        related_ids = await ncbi_client.link(
            database_from=source_database, database_to=target_database, ids=ids
        )
        logger.info(f"Found {len(related_ids)} related records")

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
        logger.error(f"Link query failed from '{source_database}' to '{target_database}': {str(e)}", exc_info=True)
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

    logger.info(f"Retrieving database info for: {database or 'all databases'}")
    
    try:
        info = await ncbi_client.info(database=database)
        logger.debug(f"Database info retrieved successfully")
        
        return json.dumps(
            {"success": True, "database": database, "info": info}, indent=2
        )

    except Exception as e:
        logger.error(f"Failed to retrieve database info: {str(e)}", exc_info=True)
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

    logger.info("Listing available NCBI databases")
    
    try:
        databases = await ncbi_client.get_databases()
        logger.info(f"Retrieved {len(databases)} databases")
        
        return json.dumps(
            {"success": True, "databases": databases, "count": len(databases)}, indent=2
        )

    except Exception as e:
        logger.error(f"Failed to list databases: {str(e)}", exc_info=True)
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

    logger.info(f"Starting BLAST search: program={program}, database={database}")
    logger.debug(f"BLAST parameters: expect={expect_value}, word_size={word_size}, matrix={matrix}, megablast={megablast}")
    
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
        
        logger.info(f"BLAST search completed: RID={result.rid}, status={result.status}")

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
        logger.error(f"BLAST search failed: program={program}, database={database}, error={str(e)}", exc_info=True)
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
  - megablast option available only on blastn for highly similar sequences

- **blastp**: Protein-protein BLAST  
  - Compares amino acid query sequences against protein sequence databases
  - Best for protein sequences

- **blastx**: Nucleotide-protein BLAST
  - Compares nucleotide query sequences translated in all frames against protein databases
  - Useful for finding protein matches for DNA sequences
  - Good for gene prediction from short nucleotide sequences; long sequences may fail due to resource limits

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
-- **slow** search for distant nucleotide homology with full alignments returned
```
blast_search(
    program="blastn",
    database="nt", 
    sequence="ATCGATCGATCG",
    expect_value=0.001
)
```
-- **fast** run a megablast search for very similar nucleotide sequences, only hit metadata returned, no alignement strings
```
blast_search(
    program="blastn",
    database="nt", 
    sequence="ATCGATCGATCG",
    expect_value=0.001
    output_fmt="summary",
    megablast=True
)
```
"""


# Add logging level handler to advertise logging capability
@mcp._mcp_server.set_logging_level()
async def handle_set_logging_level(level: str) -> None:
    """Handle dynamic log level changes from MCP client.
    
    This handler allows MCP clients to change the server's minimum log level at runtime
    by sending a logging/setLevel request. The server will only send log messages at or
    above the specified level to clients via notifications/message notifications.
    
    The presence of this handler causes the server to advertise the logging capability
    in its ServerCapabilities during the MCP initialization handshake.
    
    Args:
        level: The minimum log level (debug, info, notice, warning, error, critical, alert, emergency)
               Note: Per MCP spec, levels are lowercase
    """
    logger.info(f"Log level changed to: {level.upper()}")
    
    # Convert MCP log level (lowercase) to Python logging level (uppercase)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Update the root logger level
    logging.getLogger().setLevel(numeric_level)
    
    # Also update our specific loggers
    logging.getLogger("ncbi_mcp_server").setLevel(numeric_level)


def main():
    """Main entry point for the server."""
    # Logging is automatically configured by FastMCP using FASTMCP_LOG_LEVEL environment variable
    # The MCP client can also dynamically set the log level using the logging/setLevel request
    mcp.run()


if __name__ == "__main__":
    main()
