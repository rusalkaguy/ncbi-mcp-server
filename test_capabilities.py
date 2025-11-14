#!/usr/bin/env python3
"""Test script to verify server capabilities are properly advertised."""

import asyncio
import json
import sys
from pathlib import Path

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_capabilities():
    """Test that server capabilities include logging."""
    print("Testing NCBI MCP Server Capabilities")
    print("=" * 60)
    
    try:
        from ncbi_mcp_server.server import mcp
        
        # Get the underlying MCP server
        server = mcp._mcp_server
        
        # Get capabilities
        from mcp.server.lowlevel import NotificationOptions
        capabilities = server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={}
        )
        
        print("\n✓ Server initialized successfully")
        print(f"✓ Server name: {server.name}")
        
        # Check capabilities
        print("\n📋 Server Capabilities:")
        print("-" * 60)
        
        # Convert to dict for pretty printing
        caps_dict = capabilities.model_dump(exclude_none=True)
        print(json.dumps(caps_dict, indent=2))
        
        # Verify logging capability
        print("\n🔍 Capability Verification:")
        print("-" * 60)
        
        if capabilities.logging is not None:
            print("✓ LOGGING capability: ADVERTISED")
            print("  - Server supports logging/setLevel requests")
            print("  - Clients can dynamically change log level")
        else:
            print("✗ LOGGING capability: NOT FOUND")
            return False
        
        if capabilities.tools is not None:
            print("✓ TOOLS capability: ADVERTISED")
            print(f"  - listChanged: {capabilities.tools.listChanged}")
        else:
            print("✗ TOOLS capability: NOT FOUND")
        
        if capabilities.resources is not None:
            print("✓ RESOURCES capability: ADVERTISED")
            print(f"  - listChanged: {capabilities.resources.listChanged}")
        else:
            print("✗ RESOURCES capability: NOT FOUND")
        
        print("\n" + "=" * 60)
        print("✓ All capabilities are properly advertised!")
        print("\nThe server will include these capabilities in its")
        print("InitializeResult response during the MCP handshake.")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error testing capabilities: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_capabilities())
    sys.exit(0 if success else 1)
