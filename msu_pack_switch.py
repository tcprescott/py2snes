import py2snes
import asyncio
import datetime

async def main():
    snes = py2snes.snes()
    await snes.connect()
    print(await snes.DeviceList())
    await snes.Attach("COM3")
    print(await snes.Info())

    # get the number of packs, and the currently playing pack
    print("{time} - {value}".format(
        time=datetime.datetime.now(),
        value=list(await snes.GetAddress(0xF650AA, 2))
    ))

    # set the new pack
    await snes.PutAddress(
        [
            (0xF650AC, [0x00])
        ]
    )

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())