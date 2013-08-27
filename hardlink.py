#!/usr/bin/python

import sys
import os
import hashlib      #check_file
import re           #file_is_excluded
import math         #convert_size
import argparse

#import pprint

file_by_inode = {}
inode_by_hash  = {}

conf = {}
conf['white_list_res'] = []
conf['black_list_res'] = []
conf['_exclude_dirs_default'] = (".git", ".hg", "drafts", "Entw&APw-rfe")
conf['interactive'] = False
conf['dryrun'] = False
conf['user'] = False
conf['group'] = False
conf['ctime'] = False
conf['_read_compare_size'] = 4 * 1024
conf['_read_hash_size'] = 2 * 1024
conf['_num_links']=0
conf['_disk_saved']=0

def main():
    conf['interactive'] = True

    #TODO crude
    directories = sys.argv[1:]

    parse_arguments()
    hardlink(directories)
    return 0

def parse_arguments():
    #TODO - parseing is missing
    conf['dryrun']=False
    conf['white_list_res'] = [r"/\d+\.$"]
    conf['black_list_res'] = []
    conf['exclude_dirs'] = []

    #compile settings
    conf['exclude_dirs'].extend( [ x.lower() for x in conf['_exclude_dirs_default']] )
    conf['_compiled_white_list_res'] = [ re.compile(reg) for reg in conf['white_list_res'] ]
    conf['_compiled_black_list_res'] = [ re.compile(reg) for reg in conf['black_list_res'] ]

def hardlink(directories):
    for root in directories:
        for dirpath, dirnames, filenames in os.walk(root):
            for d in dirnames:
                if dir_is_excluded(dirpath,d):
                    dirnames.remove(d)

            for f in filenames:
                filename=os.path.join(dirpath, f)
                check_file(filename)

    if conf['interactive']:
        print("   links created: %s" % conf['_num_links'])
        print("disk space saved: %s" % str(convert_size(conf['_disk_saved'])))

def check_file(filename):
    #is the file excluded
    if file_is_excluded(filename):
        if conf['interactive']:
            print("file excluded: %s" % filename)
        return


    stat_info = os.stat(filename)
    inode_key=(stat_info.st_dev,stat_info.st_ino)

    #file is already existent
    if inode_key in file_by_inode:
        return

    # file is not linked - is there some other file with the same content
    with open(filename,'rb') as file_handle:
        content_hash=hashlib.md5(file_handle.read(conf['_read_hash_size'])).hexdigest()

    if content_hash in inode_by_hash:
        # there is some other file
        other_inode_key=inode_by_hash[content_hash]

        if inode_key[0] == other_inode_key[0]:
            # the other file is one the same drive
            file_to_link_to=file_by_inode[other_inode_key]
            if not files_are_not_allowed_to_link(file_to_link_to, filename):
                link_files(file_to_link_to, filename) #do it
            return

    #we do not have a filename for the inode
    #and the contents do not macht a file on the same device
    file_by_inode[inode_key]=filename
    inode_by_hash[content_hash]=inode_key


def link_files(file_to_link_to, filename):
    if conf['interactive'] and not conf['dryrun']:
        print("linking: %s <- %s" % (file_to_link_to,filename))

    if conf['interactive'] and conf['dryrun']:
        print("dryrun: %s <- %s" % (file_to_link_to,filename))
        conf['_num_links'] += 1
        conf['_disk_saved'] += os.stat(filename).st_size

    #DO NOT MESS WITH THIS
    if conf['dryrun']:
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

    conf['_num_links'] += 1
    conf['_disk_saved'] += os.stat(filename).st_size

    return #end of link_files

def dir_is_excluded(dirpath,dirname,interactive):
    if (os.path.basename(dirname).lower() in exclude_dirs):
        if interactive:
            print("ignoring directory: %s/%s" % (os.path.abspath(dirpath),dirname))
        return True
    return False

def file_is_excluded(filename):
    if os.path.islink(filename):
            return True

    if conf['_compiled_black_list_res']:
        for reg in conf['_compiled_black_list_res']:
            if reg.search(filename):
                return True

    if conf['_compiled_white_list_res']:
        white_re_match=False
        for reg in conf['_compiled_white_list_res']:
            if reg.search(filename):
                white_re_match=True
                break
        if not white_re_match:
            return True

    return False

def files_are_not_allowed_to_link(file_to_link_to, filename):
    file1=file_to_link_to
    file2=filename

    stat_1=os.stat(file1)
    stat_2=os.stat(file2)

    if conf['user']:
        if stat_1.st_uid != stat_2.st_uid:
            return True

    if conf['group']:
        if stat_1.st_gid != stat_2.st_gid:
            return True

    if conf['ctime']:
        if stat_1.st_ctime != stat_2.st_ctime:
            return True

    # compare contents chunk by chunk
    # with foo,bar does not work in 2.6.6
    with open(file_to_link_to, 'rb') as f1:
        with open(filename, 'rb') as f2:
            while True:
                b1 = f1.read(conf['_read_compare_size'])
                b2 = f2.read(conf['_read_compare_size'])
                if b1 != b2:
                    return True
                if not b1:
                    break

    return False #file is allowed to be linked

def convert_size(size):
    if size == 0:
        return '0B'
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size,1024)))
    p = math.pow(1024,i)
    s = round(size/p,2)
    if (s > 0):
        print(str(i))
        return '%s %s' % (s,size_name[i])
    else:
        return '0B'

if __name__ == '__main__':
    sys.exit(main())
