__version__ = '0.2.0'

import websockets
import json
from pathlib import Path

import asyncio

import logging

class usb2snesException(Exception):
    pass

SNES_DISCONNECTED = 0
SNES_CONNECTING = 1
SNES_CONNECTED = 2
SNES_ATTACHED = 3

ROM_START = 0x000000
WRAM_START = 0xF50000
WRAM_SIZE = 0x20000
SRAM_START = 0xE00000

class snes():
    def __init__(self):
        self.socket = None
        self.recv_queue = asyncio.Queue()
        self.request_lock = asyncio.Lock()
        self.is_sd2snes = False
        # self.attached = False

    async def connect(self, address='ws://localhost:8080'):
        if self.socket is not None:
            print('Already connected to snes')
            return

        self.state = SNES_CONNECTING
        recv_task = None

        print("Connecting to QUsb2snes at %s ..." % address)

        try:
            self.socket = await websockets.connect(address, ping_timeout=None, ping_interval=None)
            self.state = SNES_CONNECTED
        except Exception as e:
            if self.socket is not None:
                if not self.socket.closed:
                    await self.socket.close()
                self.socket = None
            self.state = SNES_DISCONNECTED

        self.recv_task = asyncio.create_task(self.recv_loop())

    async def DeviceList(self):
        await self.request_lock.acquire()

        if self.state < SNES_CONNECTED or self.socket is None or not self.socket.open or self.socket.closed:
            return None
        try:
            request = {
                "Opcode" : "DeviceList",
                "Space" : "SNES",
            }
            await self.socket.send(json.dumps(request))

            reply = json.loads(await asyncio.wait_for(self.recv_queue.get(), 5))
            devices = reply['Results'] if 'Results' in reply and len(reply['Results']) > 0 else None

            if not devices:
                raise Exception('No device found')

            return devices
        except Exception as e:
            if self.socket is not None:
                if not self.socket.closed:
                    await self.socket.close()
                self.socket = None
            self.state = SNES_DISCONNECTED
        finally:
            self.request_lock.release()

    async def Attach(self, device):
        if self.state != SNES_CONNECTED or self.socket is None or not self.socket.open or self.socket.closed:
            return None
        try:
            request = {
                "Opcode" : "Attach",
                "Space" : "SNES",
                "Operands" : [device]
            }
            await self.socket.send(json.dumps(request))
            self.state = SNES_ATTACHED

            if 'SD2SNES'.lower() in device.lower() or (len(device) == 4 and device[:3] == 'COM'):
                self.is_sd2snes = True
            else:
                self.is_sd2snes = False

            self.device = device

        except Exception as e:
            if self.socket is not None:
                if not self.socket.closed:
                    await self.socket.close()
                self.socket = None
            self.snes_state = SNES_DISCONNECTED

    async def Info(self):
        try:
            await self.request_lock.acquire()

            if self.state != SNES_ATTACHED or self.socket is None or not self.socket.open or self.socket.closed:
                return None
            try:
                request = {
                    "Opcode" : "Info",
                    "Space" : "SNES",
                    "Operands" : [self.device]
                }
                await self.socket.send(json.dumps(request))
                reply = json.loads(await asyncio.wait_for(self.recv_queue.get(), 5))
                info = reply['Results'] if 'Results' in reply and len(reply['Results']) > 0 else None
                return {
                    "firmwareversion": _listitem(info,0),
                    "versionstring": _listitem(info,1),
                    "romrunning": _listitem(info,2),
                    "flag1": _listitem(info,3),
                    "flag2": _listitem(info,4),
                }
            except Exception as e:
                if self.socket is not None:
                    if not self.socket.closed:
                        await self.socket.close()
                    self.socket = None
                self.snes_state = SNES_DISCONNECTED
        finally:
            self.request_lock.release()

    async def Name(self, name):
        await self.request_lock.acquire()

        if self.state != SNES_ATTACHED or self.socket is None or not self.socket.open or self.socket.closed:
            return None
        try:
            request = {
                "Opcode" : "Name",
                "Space" : "SNES",
                "Operands" : [name]
            }
            await self.socket.send(json.dumps(request))
        except Exception as e:
            if self.socket is not None:
                if not self.socket.closed:
                    await self.socket.close()
                self.socket = None
            self.state = SNES_DISCONNECTED

    async def Boot(self, rom):
        await self.request_lock.acquire()

        if self.state != SNES_ATTACHED or self.socket is None or not self.socket.open or self.socket.closed:
            return None
        try:
            request = {
                "Opcode" : "Boot",
                "Space" : "SNES",
                "Operands" : [rom]
            }
            await self.socket.send(json.dumps(request))
        except Exception as e:
            if self.socket is not None:
                if not self.socket.closed:
                    await self.socket.close()
                self.socket = None
            self.state = SNES_DISCONNECTED

    async def Menu(self):
        if self.state != SNES_ATTACHED or self.socket is None or not self.socket.open or self.socket.closed:
            return None
        try:
            request = {
                "Opcode" : "Menu",
                "Space" : "SNES",
            }
            print(json.dumps(request))
            await self.socket.send(json.dumps(request))
        except Exception as e:
            if self.socket is not None:
                if not self.socket.closed:
                    await self.socket.close()
                self.socket = None
            self.state = SNES_DISCONNECTED

    async def Reset(self):
        if self.state != SNES_ATTACHED or self.socket is None or not self.socket.open or self.socket.closed:
            return None
        try:
            request = {
                "Opcode" : "Reset",
                "Space" : "SNES",
            }
            await self.socket.send(json.dumps(request))
        except Exception as e:
            if self.socket is not None:
                if not self.socket.closed:
                    await self.socket.close()
                self.socket = None
            self.state = SNES_DISCONNECTED

    async def GetAddress(self, address, size):
        try:
            await self.request_lock.acquire()

            if self.state != SNES_ATTACHED or self.socket is None or not self.socket.open or self.socket.closed:
                return None

            GetAddress_Request = {
                "Opcode" : "GetAddress",
                "Space" : "SNES",
                "Operands" : [hex(address)[2:], hex(size)[2:]]
            }
            try:
                await self.socket.send(json.dumps(GetAddress_Request))
            except websockets.ConnectionClosed:
                return None

            data = bytes()
            while len(data) < size:
                try:
                    data += await asyncio.wait_for(self.recv_queue.get(), 5)
                except asyncio.TimeoutError:
                    break

            if len(data) != size:
                print('Error reading %s, requested %d bytes, received %d' % (hex(address), size, len(data)))
                if len(data):
                    print(str(data))
                if self.socket is not None and not self.socket.closed:
                    await self.socket.close()
                return None

            return data
        finally:
            self.request_lock.release()

    async def PutAddress(self, write_list):
        try:
            await self.request_lock.acquire()

            if self.state != SNES_ATTACHED or self.socket is None or not self.socket.open or self.socket.closed:
                return False

            PutAddress_Request = {
                "Opcode" : "PutAddress",
                "Operands" : []
            }

            if self.is_sd2snes:
                cmd = b'\x00\xE2\x20\x48\xEB\x48'

                for address, data in write_list:
                    if (address < WRAM_START) or ((address + len(data)) > (WRAM_START + WRAM_SIZE)):
                        print("SD2SNES: Write out of range %s (%d)" % (hex(address), len(data)))
                        return False
                    for ptr, byte in enumerate(data, address + 0x7E0000 - WRAM_START):
                        cmd += b'\xA9' # LDA
                        cmd += bytes([byte])
                        cmd += b'\x8F' # STA.l
                        cmd += bytes([ptr & 0xFF, (ptr >> 8) & 0xFF, (ptr >> 16) & 0xFF])

                cmd += b'\xA9\x00\x8F\x00\x2C\x00\x68\xEB\x68\x28\x6C\xEA\xFF\x08'

                PutAddress_Request['Space'] = 'CMD'
                PutAddress_Request['Operands'] = ["2C00", hex(len(cmd)-1)[2:], "2C00", "1"]
                try:
                    if self.socket is not None:
                        await self.socket.send(json.dumps(PutAddress_Request))
                    if self.socket is not None:
                        await self.socket.send(cmd)
                except websockets.ConnectionClosed:
                    return False
            else:
                PutAddress_Request['Space'] = 'SNES'
                try:
                    #will pack those requests as soon as qusb2snes actually supports that for real
                    for address, data in write_list:
                        PutAddress_Request['Operands'] = [hex(address)[2:], hex(len(data))[2:]]
                        if self.socket is not None:
                            await self.socket.send(json.dumps(PutAddress_Request))
                        if self.socket is not None:
                            await self.socket.send(data)
                except websockets.ConnectionClosed:
                    return False

            return True
        finally:
            self.request_lock.release()

    async def recv_loop(self):
        try:
            async for msg in self.socket:
                self.recv_queue.put_nowait(msg)
        except Exception as e:
            if type(e) is not websockets.ConnectionClosed:
                logging.exception(e)
        finally:
            socket, self.socket = self.socket, None
            if socket is not None and not socket.closed:
                await socket.close()

            self.state = SNES_DISCONNECTED
            self.recv_queue = asyncio.Queue()

    # def GetFile(self,filepath):
    #     """Not yet fully implemented"""
    #     if self.attached:
    #         cmd = {
    #             'Opcode': 'GetFile',
    #             'Space': 'SNES',
    #             'Flags': None,
    #             'Operands': [filepath]
    #         }
    #         self.conn.send(json.dumps(cmd))
    #         result = self.conn.recv()
    #         binAnswer = self.conn.recv_data()
    #         fh = open('rom/testget.sfc','wb')
    #         fh.write(binAnswer[1])
    #         fh.close()
    #         return json.loads(result)['Results']
    #     else:
    #         raise usb2snesException("GetFile: not attached to usb2snes.  Try executing Attach first.")

    # def List(self,dirpath):
    #     if not self.attached:
    #         raise usb2snesException("Not attached to usb2snes.  Try executing Attach first.")
    #     elif not dirpath.startswith('/') and not dirpath in ['','/']:
    #         raise usb2snesException("Path \"{path}\" should start with \"/\"".format(
    #             path=dirpath
    #         ))
    #     elif dirpath.endswith('/') and not dirpath in ['','/']:
    #         raise usb2snesException("Path \"{path}\" should not end with \"/\"".format(
    #             path=dirpath
    #         ))

    #     if not dirpath in ['','/']:
    #         path = dirpath.lower().split('/')
    #         for idx, node in enumerate(path):
    #             if node == '':
    #                 continue
    #             else:
    #                 parent = '/'.join(path[:idx])
    #                 parentlist = self._list(parent)
                    
    #                 if any(d['filename'].lower() == node for d in parentlist):
    #                     continue
    #                 else:
    #                     raise FileNotFoundError("directory {path} does not exist on usb2snes.".format(
    #                         path=dirpath
    #                     ))
    #         return self._list(dirpath)
    #     else:
    #         return self._list(dirpath)

    # def MakeDir(self,dirpath):
    #     if not self.attached:
    #         raise usb2snesException("Not attached to usb2snes.  Try executing Attach first.")
    #     if dirpath in ['','/']:
    #         raise usb2snesException('MakeDir: dirpath cannot be blank or \"/\"')

    #     path = dirpath.split('/')
    #     parent = '/'.join(path[:-1])
    #     parentdir = self.List(parent)
    #     try:
    #         self.List(dirpath)
    #     except FileNotFoundError as e:
    #         self._makedir(dirpath)

    # def Remove(self,filepath):
    #     if self.attached:
    #         if not filepath in ['','/']:
    #             # self._makedir(dirpath)
    #             path = filepath.split('/')
    #             parent = '/'.join(path[:-1])
    #             parentdir = self.List(parent)
    #             if parentdir:
    #                 # print(self.List(dirpath))
    #                 if not self.List(filepath):
    #                     self._makedir(filepath)
    #                 return True
    #             else:
    #                 raise usb2snesException('MakeDir: cannot create {filepath} because parent directory {parent} does not exist.'.format(
    #                     dirpath=filepath,
    #                     parent=parent
    #                 ))
    #         else:
    #             raise usb2snesException('Remove: filepath cannot be blank or /')
    #     else:
    #         raise usb2snesException("Remove: not attached to usb2snes.  Try executing Attach first.")



    # def _list(self, dirpath):
    #     cmd = {
    #         'Opcode': 'List',
    #         'Space': 'SNES',
    #         'Flags': None,
    #         'Operands': [dirpath]
    #     }
    #     self.conn.send(json.dumps(cmd))
    #     result = self.conn.recv()
    #     it = iter(json.loads(result)['Results'])
    #     resultlist = []
    #     for item in it:
    #         filetype = item
    #         filename = next(it)
    #         resultdict = {
    #             "type": filetype,
    #             "filename": filename
    #         }
    #         if not filename in ['.','..']:
    #             resultlist.append(resultdict)
    #     return resultlist
        

    # def _makedir(self, dirpath):
    #     cmd = {
    #         'Opcode': 'MakeDir',
    #         'Space': 'SNES',
    #         'Flags': None,
    #         'Operands': [dirpath]
    #     }
    #     self.conn.send(json.dumps(cmd))

    # def _remove(self, filepath):
    #     cmd = {
    #         'Opcode': 'Remove',
    #         'Space': 'SNES',
    #         'Flags': None,
    #         'Operands': [filepath]
    #     }
    #     self.conn.send(json.dumps(cmd))

    # def _fileexists(self, filepath):
    #     pass

def _chunk(iterator, count):
    itr = iter(iterator)
    while True:
        yield tuple([next(itr) for i in range(count)])

def _listitem(list, index):
    try:
        return list[index]
    except IndexError:
        return None