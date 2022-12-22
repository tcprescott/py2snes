import py2snes
import asyncio
import datetime

async def main():
    snes = py2snes.snes()
    await snes.connect()
    devices = await snes.DeviceList()
    await snes.Attach(devices[0])
    print(await snes.Info())

    # await snes.PutFile('testing/ALttP - VT_no-glitches-30_normal-open_randomized-ganon_35Mz2221ME.sfc', '/romloader/testfile.sfc')
    await snes.Remove('/romloader/testfile.sfc')

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())