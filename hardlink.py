#!/usr/bin/python


import sys
import os
import hashlib
import argparse
import pprint

file_by_inode = {}
inode_by_hash  = {}

exclude_dirs = []

conf = {}
conf[dr]


def main():
    dryrun=True
    interactive=True
    parse_arguments()
    directories = sys.argv[1:]
    hardlink(directories, dryrun, interactive)
    return 0

def parse_arguments():
    pass

def hardlink(directories,dryrun=True,interactive=False):
    exclude_dirs_default = (".git",".hg","drafts","Entw&APw-rfe")
    global exclude_dirs
    exclude_dirs += [ x.lower() for x in exclude_dirs_default ]
    for root in directories:
        for dirpath, dirnames, filenames in os.walk(root):
            for d in dirnames:
                if dir_is_excluded(dirpath,d,interactive):
                    dirnames.remove(d)

            for f in filenames:
                filename=os.path.join(dirpath, f)
                check_file(filename, dryrun, interactive)

def check_file(filename, dryrun, interactive):
    #is the file excluded
    if file_is_excluded(filename):
        return

    stat_info = os.stat(filename)
    inode_key=(stat_info.st_dev,stat_info.st_ino)

    #file is already existent
    if inode_key in file_by_inode:
        return

    # file is not linked - is there some other file with the same content
    with open(filename,'rb') as file_handle:
        content_hash=hashlib.md5(file_handle.read()).hexdigest()

    if content_hash in inode_by_hash:
        # there is some other file
        other_inode_key=inode_by_hash[content_hash]

        if inode_key[0] == other_inode_key[0]:
            # the other file is one the same drive
            link_files(file_by_inode[other_inode_key], filename, dryrun, interactive) #do it
            return

    #we do not have a filename for the inode
    #and the contents do not macht a file on the same device
    file_by_inode[inode_key]=filename
    inode_by_hash[content_hash]=inode_key


def link_files(file_to_link_to, filename, dryrun, interactive):
    if file_is_excluded(file_to_link_to,filename):
        return

    if interactive and not dryrun:
        print("linking: %s <- %s" % (file_to_link_to,filename))

    if dryrun:
        print("dryrun: %s <- %s" % (file_to_link_to,filename))
        return

    temp_name=filename + "___link_it___"
    try:
        os.rename(filename,temp_name)
    except:
        print("failed to rename %s to %s" % (filename,temp_name))
        return

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

    try:
        os.unlink(temp_name)
    except:
        print("failed to unlink %s" % temp_name)


def dir_is_excluded(dirpath,dirname,interactive):
    if (os.path.basename(dirname).lower() in exclude_dirs):
        if interactive:
            print("ignoring directory: %s/%s" % (os.path.abspath(dirpath),dirname))
        return True
    return False


def file_is_excluded(filename,other_file=None,date=False):
    if not other_file:
        if os.path.islink(filename):
            return True
        #if matches some exclude re
            #return False
    else:
        if False:
            #extra checks like same id, timestamps, etc here
            return True

    return False

if __name__ == '__main__':
    sys.exit(main())
