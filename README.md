# sandbag
Attempting to create a public-facing read-only NBD server that can create volumes that Linux users can mount over the Internet.

We use HTTP, FTP, RSYNC and the rest because we want to promote interoperabilty between all of the different OSs.  I can host my website on Linux and you can read it on Mac.  That's amazing.

But what about content that is exclusively served to GNU+Linux users?  I feel that there is a lot of value to be obtained by serving certain content to Linux users over volumes hosted on NBD servers and mounted over the Internet.  A very simple example would be a rescue CD.  You can boot a kernel that's been built to establish a connection to this image created for the purpose and that is hosted somewhere on the Internet and mount it for use.

This image could be absolutely huge, hosting a great many tarballs and other content that might be useful to a user who is installing or repairing his Linux installation but mounting it does not mean the user is downloading the entire image.  It's just like a normal disk in that respect, only when you go to read a file do you instruct the file system to read blocks for it from the underlying block device.  The only difference is that since this block device is accessed over the Internet, though it may allow you to access hundreds of megabytes of content, it only a takes a few megabytes of space on your hard disk, and is being constantly updated.

Another example is introducing new methods for distros to deliver content to their users.  I'm a fan of Gentoo, which is a source-based distrubution.  Gentoo makes available the many tarballs that go into making a running GNU+Linux system to its users.  This uses a lot of bandwidth and they'd like to find a way to reduce that use.

Unlike other distributions, Gentoo is source-based, which means that the user is actually guided through the process of downloading the tarball, extracting it, patching it, building it and finally installing it.  When a project is updated, very often the change only occurs in a very few files, but the tarball needs to be rebuilt regardless and the bandwidth must be spent on getting it to the user's system.

Gentoo uses rsync to let users update their portage trees, which is kind of system blueprint that lets users exactly detail their installations.  But distfiles--the package tarballs--are fetched over ftp and http.

What I would like to see is Gentoo users being able to run rsync on their project trees as well as their portage trees.  But that would be an absolutely enormous directory and I don't know how well a rsync server would fare with that, especially with so many users.

A better alternative might be to mount that directory from a filesystem sitting on a NBD server.  The rsync is now performed by the user's computer, relieving Gentoo of that load.  There are blocks being downloaded to satisfy the rsync of course--locating files alone is quite a few I imagine--but then if the result is that only a few small files are downloaded to the users computer instead of the great big tarball, there's a good chance the tradeoff might be worth it.

Anyways, it's difficult today to recommend solutions like this when there is as far as I can tell no software designed to let people host NBD volumes in a public-facing way on the Internet.  Yes, there are a lot of NBD servers out there, but they all assume friendly, limited and/or controlled use.

This has to be a server that takes to heart the many lessons learned by the ftp and http guys over the years, because people pound these servers for sport.

My hope: though the lessons maybe be many, meeting them head on and adapting them to the block device model is going to be fun and easy in Python.  And maybe the thing I like most about Linux is the block device model and the way you can stack devices together in combinations and achieve many amazing results.

For instance, hosting a repository on a block device is all well and good.  But what if you have many block devices out there that are all hosting exactly the same content?  Wouldn't it be great if you could mount all of them and then divide your many block requests amongst them all, in a bid to improve latency?  Well, since you're a Linux user, you can use dmraid, which lets you do just that.

What about, if we wanted to partition block requests between two groups of users: those are regular users accessing a limited quantity of newly released content, and those who appear to be performing more indiscriminate downloads.  So, what about creating dmheatmap, which takes two block devices, one which expedites requests and the other which queues them, and forwards requests according to how popular they are (popular suggests newly released content suggests responsible use, whereas requested unformatted blocks suggests otherwise, etc.)

As a NBD server, we can store metadata for every block.  Date, when last accessed, how often used.  What can you create that exploits this to create a better experience using GNU+Linux?  Apparently, everything.

But what I can do for now...

A simple script written using Python and asyncio that lets an administrator create a number of queues into which requests may be placed and parameters describing how requests are mapped to these queues.

There is a parameter called --rate that accepts a series of tuples, like this:  ((1000, 10), (10000, 4), (100000, 2))

Each tuple contains the two numbers.  The first is a number of blocks.  When a task is queued, we look at the number of blocks delivered to that client so far.  If it is less than the number of blocks set for a queue, then it gets placed into it.

There is another task which is responsible for scheduling their execution.  It uses the second number to determine how many tasks to pull from that queue for execution in this iteration.  An iteration is simply our sending the one big group of tasks to asyncio to be executed.  The sum of the second numbers in the series determines the maximum number of tasks we tell asyncio to process each time through the loop.  Big powerful systems can use larger numbers than small, less powerful systems.

So in the example above, this would be an instruction to the server to look at the number of blocks requested by that client thus far when selecting from one of the four queues; one queue for clients who've made fewer than 1000 block requests and that processes 10 tasks at a time, one queue for clients who've made fewer than 10000 block requests and that processes 4 tasks at a time, one queue for clients with less than 100000 block requests that gets processed 2 tasks at a time, and then finally there's an implicit tuple which catches all other tasks and processes them one at a time.

The point of all of this is to hopefully manage access to the block device so that everybody gets a shot at downloading what they need.  People who abuse the bandwidth see their throughput throttled.  People who don't, don't.

There are no doubt other abuses that will pose challenges to be met but the simplicity of the NBD protocol (fixed-length, binary) together with the fact that the Linux kernel is our client bodes very well I think for the effort.
