"""Real MCP client/server handshake over stdio, using synthetic records only."""
import asyncio,sys,unittest
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
class TransportTest(unittest.TestCase):
 def test_stdio(self):
  async def run():
   code="from server import create_server; from bridge import Bridge; from test_bridge import FakeAPI; create_server(Bridge(FakeAPI(),['allowed'])).run(transport='stdio')"
   params=StdioServerParameters(command=sys.executable,args=['-c',code],cwd=str(Path(__file__).parent.resolve()))
   async with stdio_client(params) as (read,write):
    async with ClientSession(read,write) as client:
     await client.initialize();tools=await client.list_tools();self.assertEqual(len(tools.tools),6)
     r=await client.call_tool('livepage_read_content',{'content_id':'p'});self.assertFalse(r.isError)
     denied=await client.call_tool('livepage_read_content',{'content_id':'secret'});self.assertTrue(denied.isError)
     download=await client.call_tool('livepage_get_asset',{'content_id':'p','kind':'image'});self.assertTrue(download.isError)
  asyncio.run(run())
if __name__=='__main__':unittest.main()
