#!/usr/bin/python


# Copyright 2013 Jan Christoph Uhde <Jan@UhdeJC.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#
# The current sourcecode can be found at:
#
#   https://github.com/ObiWahn/
#


#
# How it works:
#
# For each file that is not a symbolic link a md5 hash is created.
#


import sys
import os
import hashlib      #check_file
import re           #file_is_excluded
import math         #convert_size

import pprint

file_by_inode = {}
inode_by_hash  = {}

class hardConf:
    '''my great documenmtation about hardConf

    here we go...
    '''

    #: my documentation string about directories
    directories        = []

    white_list_res     = []
    black_list_res     = []
    exclude_dirs       = []
    _exclude_dirs_default = (".git", ".hg", "drafts", "Entw&APw-rfe")

    interactive        = False
    dryrun             = False

    user               = False
    group              = False
    mode               = False
    ctime              = False

    _read_compare_size = 4 * 1024
    _read_hash_size    = 2 * 1024
    _num_links         = 0
    _disk_saved        = 0


def main():
    conf=hardConf()
    conf.interactive = True
    parse_arguments(conf)
    if conf.directories:
        hardlink(conf)
    else:
        print("No directory given")
    return 0

def parse_arguments(conf):
    """ This function parses the arguments and manipulates the conf object
    """
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument("directory", nargs="*",
                        help="list of directories",
                        metavar="<dir>"
                       )
    parser.add_argument("-d","--dryrun", help="show what would be done", action="store_true")

    parser.add_argument("-u", "--user", help="ensure files have the same user", action="store_true")
    parser.add_argument("-g", "--group", help="ensure files have the same group", action="store_true")
    parser.add_argument("-m", "--mode", help="ensure files have the same mode", action="store_true")
    parser.add_argument("-t", "--time", help="ensure files have the same time", action="store_true")

    parser.add_argument("--whitelist",
                        help="if given files are required to match one of the REs",
                        metavar="<whitelist re>",
                        nargs="*"
                       )
    parser.add_argument("--blacklist",
                        help="if given files are not allowed to match any of the REs",
                        metavar="<blacklist re>",
                        nargs="*"
                       )

    parser.add_argument("--exclude-dir",
                        help="exclude directories with given names (not full paths - eg: .git)",
                        metavar="<dir>",
                        nargs="*"
                       )


    args=parser.parse_args()

    if args.directory:
        conf.directories.extend(args.directory)

    if args.dryrun:
        conf.dryrun=args.dryrun

    if args.user:
        conf.user=args.user
    if args.group:
        conf.group=args.group
    if args.mode:
        conf.mode=args.mode
    if args.time:
        conf.time=args.time

    if args.whitelist:
        conf.white_list_res.extend(args.whitelist)
    if args.blacklist:
        conf.black_list_res.extend(args.blacklist)
    if args.exclude_dir:
        conf.exclude_dirs.extend(exclude_dir)



def hardlink(conf):
    #compile settings
    conf.exclude_dirs.extend( [ x.lower() for x in conf._exclude_dirs_default] )
    conf._compiled_white_list_res = [ re.compile(reg) for reg in conf.white_list_res ]
    conf._compiled_black_list_res = [ re.compile(reg) for reg in conf.black_list_res ]

    # walk directories
    for root in conf.directories:
        for dirpath, dirnames, filenames in os.walk(root):
            for d in dirnames:
                if dir_is_excluded(conf, dirpath, d):
                    dirnames.remove(d)

            for f in filenames:
                filename=os.path.join(dirpath, f)
                check_file(conf, filename)

    if conf.interactive:
        print("   links created: %s" % conf._num_links)
        print("disk space saved: %s" % str(convert_size(conf._disk_saved)))

def check_file(conf, filename):
    #is the file excluded
    if file_is_excluded( filename
                       , conf._compiled_white_list_res
                       , conf._compiled_black_list_res
                       ):
        if conf.interactive:
            print("file excluded: %s" % filename)
        return

    stat_info = os.stat(filename)
    inode_key=(stat_info.st_dev,stat_info.st_ino)

    #file is already existent
    if inode_key in file_by_inode:
        return

    # file is not linked - is there some other file with the same content
    with open(filename,'rb') as file_handle:
        content_hash=hashlib.md5(file_handle.read(conf._read_hash_size)).hexdigest()

    if content_hash in inode_by_hash:
        # there is some other file
        other_inode_key=inode_by_hash[content_hash]

        if inode_key[0] == other_inode_key[0]:
            # the other file is one the same drive
            file_to_link_to=file_by_inode[other_inode_key]
            if allowed_to_link( file_to_link_to
                              , filename
                              , conf._read_compare_size
                              , conf.user
                              , conf.group
                              , conf.mode
                              , conf.ctime
                              ):
                link_files(conf, file_to_link_to, filename) #do it
            return

    #we do not have a filename for the inode
    #and the contents do not macht a file on the same device
    file_by_inode[inode_key]=filename
    inode_by_hash[content_hash]=inode_key


def link_files(conf, file_to_link_to, filename):
    if conf.interactive and not conf.dryrun:
        print("linking: %s <- %s" % (file_to_link_to,filename))

    if conf.interactive and conf.dryrun:
        print("dryrun: %s <- %s" % (file_to_link_to,filename))
        conf._num_links += 1
        conf._disk_saved += os.stat(filename).st_size

    #DO NOT MESS WITH THIS
    if conf.dryrun:
        return

    #move original out of the way
    try:
        temp_name = filename + "__link_it__"
        os.rename(filename,temp_name)
    except:
        print("failed to rename %s to %s" % (filename,temp_name))
        return

    #link to other file
    try:
        os.link(file_to_link_to,filename)
    except:
        print("unable to link %s to %s" % (filename,file_to_link_to))
        print("trying to undo")
        try:
            os.rename(temp_name,filename)
            print("we are back at the old state")
        except Exception as e:
            print("unable to undo - this should not happen we habe messed up")
            raise e
        return

    #remove original file
    try:
        os.unlink(temp_name)
    except Exception as e:
        print("failed to unlink %s" % temp_name)
        raise e

    conf._num_links += 1
    conf._disk_saved += os.stat(filename).st_size

    return #end of link_files

def dir_is_excluded(conf, dirpath, dirname):
    if (os.path.basename(dirname).lower() in conf.exclude_dirs):
        if conf.interactive:
            print("ignoring directory: %s/%s" % (os.path.abspath(dirpath),dirname))
        return True
    return False

def file_is_excluded( filename
                    , compiled_white_list_res
                    , compiled_black_list_res
                    ):
    if os.path.islink(filename):
            return True

    if compiled_black_list_res:
        for reg in compiled_black_list_res:
            if reg.search(filename):
                return True

    if compiled_white_list_res:
        white_re_match=False
        for reg in compiled_white_list_res:
            if reg.search(filename):
                white_re_match=True
                break
        if not white_re_match:
            return True

    return False


def allowed_to_link( file_to_link_to
                   , filename
                   , read_compare_size = 4 * 1024
                   , check_user = False
                   , check_group = False
                   , check_mode = False
                   , check_ctime = False
                   ):

    file1=file_to_link_to
    file2=filename

    stat_1=os.stat(file1)
    stat_2=os.stat(file2)

    #sizes don't match
    if stat_1.st_size != stat_2.st_size:
        return False

    if check_user:
        if stat_1.st_uid != stat_2.st_uid:
            return False

    if check_group:
        if stat_1.st_gid != stat_2.st_gid:
            return False

    if check_mode:
        if stat_1.st_mode != stat_2.st_mode:
            return False

    if check_ctime:
        if stat_1.st_ctime != stat_2.st_ctime:
            return False

    # compare contents chunk by chunk
    # with foo,bar does not work in 2.6.6
    # sizes are already compared so f2 can not be longer!
    with open(file_to_link_to, 'rb') as f1:
        with open(filename, 'rb') as f2:
            while True:
                b1 = f1.read(read_compare_size)
                b2 = f2.read(read_compare_size)
                if b1 != b2:
                    return False
                if not b1:
                    break

    return True

def convert_size(size):
    if size == 0:
        return '0B'
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size,1024)))
    p = math.pow(1024,i)
    s = round(size/p,2)
    if (s > 0):
        return '%s %s' % (s,size_name[i])
    else:
        return '0B'

if __name__ == '__main__':
    sys.exit(main())
