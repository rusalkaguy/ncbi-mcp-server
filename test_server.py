#!/usr/bin/env python3
"""Simple test script for NCBI MCP Server."""

import asyncio
import os
from ncbi_mcp_server.ncbi_client import NCBIClient, NCBIConfig


async def test_ncbi_client():
    """Test basic functionality of the NCBI client."""

    # Use environment variables or defaults
    config = NCBIConfig(
        api_key=os.getenv("NCBI_API_KEY"),
        email=os.getenv("NCBI_EMAIL", "test@example.com"),
    )

    print("🧬 Testing NCBI MCP Server Client...")
    print(f"📧 Email: {config.email}")
    print(
        f"🔑 API Key: {'✅ Set' if config.api_key else '❌ Not set (using rate limits)'}"
    )
    print()

    async with NCBIClient(config) as client:
        # Test 1: List databases
        print("1️⃣ Testing database listing...")
        try:
            databases = await client.get_databases()
            print(f"   ✅ Found {len(databases)} databases")
            print(f"   📋 Sample: {', '.join(databases[:5])}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()

        # Test 2: Search PubMed
        print("2️⃣ Testing PubMed search...")
        try:
            result = await client.search(
                database="pubmed", query="CRISPR[title]", retmax=5
            )
            print(f"   ✅ Found {result.count} total papers about CRISPR")
            print(f"   📄 Retrieved {len(result.ids)} IDs: {result.ids[:3]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()

        # Test 3: Get summaries
        if "result" in locals() and result.ids:
            print("3️⃣ Testing record summaries...")
            try:
                summaries = await client.summary(
                    database="pubmed",
                    ids=result.ids[:2],  # Just test first 2
                )
                print(f"   ✅ Got summaries for {len(summaries)} papers")
                if summaries:
                    print(f"   📰 Example: {summaries[0].title[:60]}...")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            print()

        # blast test sequence
        test_sequence = "".join((
            "GGAGGAGGAGGAGGAAGAAGAAGAGGTGGAAGAGGAGGAGGAGAAAGTAGAGGAGGAAGAGGAAGCGGAG",
            "AAGGCGAAAACGAGCGGAAAGCGGACGGTTATCGGGAGTGGAAGAAGAGAGAGTGGCCAGGTGTGTCGCG",
            "GCTTCGCCGAGAAGGAGGAAGAGAACGTGGTGGAGGTCGTGGTGTGTCGTTGACGAAGAAGAAGGAAAGG",
            "AAAGAAGGTGGAGGAAGACGAGGAAGAAGAAAAGGAAGGTAGTGCTTGCTGCTCGGAGGTTGCGCAGAGA"
        ))

        # Test 4: Simple BLAST summary (this might take a while)
        print("4️⃣ Testing BLAST search - summary output (this may take 30+ seconds)...")
        try:
            blast_result = await client.blast_search(
                program="blastn",
                database="nt",
                sequence=test_sequence,  # Simple test sequence
                expect=10.0,
                output_fmt="summary",
            )
            if blast_result.status == "completed":
                print("   ✅ BLAST search completed successfully")
                if blast_result.results and "records" in blast_result.results:
                    records = blast_result.results["records"]
                    print(f"   🎯 Found {len(records)} alignment records")
                hsp0 = blast_result.results["records"][0]["alignments"][0]["hsps"][0]
                for key in ('query','match','sbjct'):
                    if key not in hsp0:
                        print(f"   🎯 '{key}' NOT in hsps.")
                    else:
                        print(f"   ❌ '{key}' present in 'hsps' output, despite 'summary' output_fmt") 
            else:
                print(f"   ⚠️ BLAST status: {blast_result.status}")
        except Exception as e:
            print(f"   ❌ BLAST Error: {e}")
        print()

        # Test 5: Simple BLAST full alignments(this might take a while)
        print("5 Testing BLAST search - full alignment output (this may take 30+ seconds)...")
        try:
            blast_result = await client.blast_search(
                program="blastn",
                database="nt",
                sequence=test_sequence,  # Simple test sequence
                expect=10.0,
            )
            if blast_result.status == "completed":
                print("   ✅ BLAST search completed successfully")
                if blast_result.results and "records" in blast_result.results:
                    records = blast_result.results["records"]
                    print(f"   🎯 Found {len(records)} alignment records")
                # check that alignments are present (full mode)
                hsp0 = blast_result.results["records"][0]["alignments"][0]["hsps"][0]
                for key in ('query','match','sbjct'):
                    if key in hsp0:
                        print(f"   🎯 '{key}' present in hsps.")
                    else:
                        print(f"   ❌ '{key}' missing from hsps in 'full' output mode.") 

            else:
                print(f"   ⚠️ BLAST status: {blast_result.status}")
        except Exception as e:
            print(f"   ❌ BLAST Error: {e}")
        print()

    print("🎉 Test completed!")
    print()
    print("💡 If all tests passed, your server should work with Claude Desktop!")
    print("💡 To test with MCP Inspector: mcp dev ncbi_mcp_server/server.py")


if __name__ == "__main__":
    asyncio.run(test_ncbi_client())
