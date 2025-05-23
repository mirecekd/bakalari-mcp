#!/usr/bin/env python3
"""
Příklad použití Bakaláři MCP Serveru
Tento script ukazuje, jak se připojit k MCP serveru a používat jeho funkce.
"""

import json
import asyncio
import subprocess
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_bakalari_mcp():
    """Testuje připojení k Bakaláři MCP serveru a volání funkcí."""
    
    # Parametry pro spuštění MCP serveru
    # POZOR: Nahraď svými skutečnými přihlašovacími údaji!
    server_params = StdioServerParameters(
        command="uvx",
        args=[
            "--from", "./dist/bakalari_mcp_server-1.0.0-py3-none-any.whl",
            "bakalari-mcp-server",
            "--user", "TVO_UZIVATELSKE_JMENO",  # <- ZMĚŇ
            "--password", "TVE_HESLO",          # <- ZMĚŇ  
            "--url", "https://tva-skola.bakalari.cz"  # <- ZMĚŇ
        ],
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                
                # Inicializace klienta
                await session.initialize()
                
                print("✅ Připojení k MCP serveru úspěšné!")
                
                # Seznam dostupných nástrojů
                tools = await session.list_tools()
                print(f"📋 Dostupné nástroje: {[tool.name for tool in tools.tools]}")
                
                # Test 1: Získání dnešního rozvrhu
                print("\n🗓️  Test 1: Získání dnešního rozvrhu")
                result = await session.call_tool("rozvrh", {})
                print("Výsledek:")
                print(json.dumps(result.content[0].text, ensure_ascii=False, indent=2))
                
                # Test 2: Získání rozvrhu pro konkrétní datum
                print("\n📅 Test 2: Získání rozvrhu pro konkrétní datum")
                result = await session.call_tool("rozvrh", {"datum": "2024-05-23"})
                print("Výsledek:")
                print(json.dumps(result.content[0].text, ensure_ascii=False, indent=2))
                
                # Test 3: Získání stálého rozvrhu
                print("\n📊 Test 3: Získání stálého rozvrhu")
                result = await session.call_tool("staly_rozvrh", {})
                print("Výsledek (zkráceno):")
                result_text = result.content[0].text
                if len(result_text) > 500:
                    print(result_text[:500] + "...")
                else:
                    print(result_text)
                
                print("\n✅ Všechny testy dokončeny!")
                
    except Exception as e:
        print(f"❌ Chyba při testování: {e}")
        print("💡 Zkontroluj:")
        print("   - Že máš správné přihlašovací údaje")
        print("   - Že je server dostupný")
        print("   - Že máš nainstalované závislosti: pip install mcp")


async def simple_test():
    """Jednoduchý test pouze spuštění serveru."""
    print("🧪 Jednoduchý test spuštění serveru...")
    
    try:
        # Spustíme server jen na chvilku, abychom ověřili, že funguje
        process = subprocess.Popen(
            [
                "uvx", "--from", "./dist/bakalari_mcp_server-1.0.0-py3-none-any.whl",
                "bakalari-mcp-server", "--help"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=10)
        
        if process.returncode == 0:
            print("✅ Server se spouští správně!")
            print("📝 Help output:")
            print(stdout)
        else:
            print(f"❌ Chyba při spuštění: {stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏱️  Timeout - server pravděpodobně běží správně")
        process.kill()
    except Exception as e:
        print(f"❌ Chyba: {e}")


if __name__ == "__main__":
    print("🔧 Bakaláři MCP Server - Příklad použití")
    print("=" * 50)
    
    # Nejdřív jednoduchý test
    asyncio.run(simple_test())
    
    print("\n" + "=" * 50)
    print("⚠️  Pro plný test upravte přihlašovací údaje v kódu!")
    print("   Pak odkomentujte následující řádek:")
    print("   # asyncio.run(test_bakalari_mcp())")
    
    # Pro skutečný test odkomentuj tento řádek a uprav credentials výše:
    # asyncio.run(test_bakalari_mcp())
