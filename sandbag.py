#!/usr/bin/env python3

import aiofiles, asyncio, argparse

class sandbag:

    def __init__(self, file, size, gate, rate):
        self.file = file
        self.size = size
        self.gate = gate
        self.rate = rate
        self.queue = [[] for i in range(len(self.rate))]
        self.event = asyncio.Event()
        self.nclients = 0

    async def send_block(self, offset, writer):
        await self.file.seek(offset * self.size)
        writer.write(await self.file.read(self.size))
        await writer.drain()

    async def add_task(self, task, nblocks):
        for i in range(len(self.rate)):
            if nblocks <= self.rate[i][0]:
                self.queue[i].append(task)
                break

    async def handle_client(self, reader, writer):
        if self.nclients < self.gate:
            self.nclients += 1
            try:
                nblocks = 0
                while request := await reader.read(16):
                    task = self.send_block(int.from_bytes(request[:8], 'big'), writer)
                    self.add_task(task, nblocks)
                    nblocks += 1
                    while True:
                        await self.event.wait()
                        if task.done():
                            break
            finally:
                self.nclients -= 1

    async def start_server(self, host, port):
        server = await asyncio.start_server(self.handle_client, host, port)
        print(f'starting sandbag on {host}:{port}')
        async with server:
            await server.serve_forever()

    async def run_tasks(self, wait):
        while True:
            v = []
            for i, q in enumerate(self.queue):
                n = min(len(q), self.rate[i][1])
                v += q[:n]
                q = q[n:]

            await asyncio.gather(*v)

            event = self.event
            self.event = asyncio.Event()
            event.set()
            await asyncio.sleep(wait)

async def run(args):
    rate = eval(args.rate) # if user inputs bad expression let it die here
    async with aiofiles.open(args.path, 'rb') as file:
        server = sandbag(file, args.size, args.gate, (*rate, (2**64, 1)))
        async with asyncio.TaskGroup() as tg:
            tg.create_task(server.start_server(host=args.host, port=args.port))
            tg.create_task(server.run_tasks(args.wait))

def main():
    parser = argparse.ArgumentParser(description='Public-facing read-only NBD server')
    parser.add_argument('--host', default='localhost',       help='host to listen on')
    parser.add_argument('--port', default=2001,  type=int,   help='port to listen on')
    parser.add_argument('--path', required=True,             help='file/device to listen on')
    parser.add_argument('--gate', default=1000,  type=int,   help='max number of clients served at once')
    parser.add_argument('--rate', default='()',              help='this gets given to python eval()')
    parser.add_argument('--size', default=512,   type=int,   help='block size for device')
    parser.add_argument('--wait', default=0.1,   type=float, help='delay at end of each inner loop')
    args = parser.parse_args()
    if 'help' in args:
        parser.print_help()
    else:
        asyncio.run(run(args), debug=True)

if __name__ == '__main__':
    main()
