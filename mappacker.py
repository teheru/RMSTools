#!/usr/bin/python3

#######################################################################################################################
## Name:        RMS Mappacker                                                                                        ##
## Description: Removes a lot of content from an Age of Empires II RMS (Random Map Script) map that does not change  ##
##              the map. This includes removing whitespace and comments, random cases which never can be reached     ##
##              and conditions that never can be reached. It also has a option to pack multiple RMS files into a     ##
##              mappack with (almost) equal percentages.                                                             ##
## Author:      Marian 'nC_eru_' Cepok, marian.cepok@gmail.com                                                       ##
## Licence:     This tool is distributed under the terms of the Modified BSD Licence.                                ##
##              For more details see copying.md which is distributed with this tool.                                 ##
#######################################################################################################################

import sys
import re
import copy
import hashlib

# parse_random() looks for random cases and analyses which cases can occur and removes those which cannot. If a random
# block can be reduces to a single 100% chance, the random block is removed and replaced by its content.
def parse_random(lines):
    chances = 0
    result = []

    chance = 0
    block = ''
    add_block = True
    # loop through the lines of the rms file and analyse one by one
    while lines:
        if lines[0].startswith('start_random'):
            lines.pop(0)
            # start a new parser (useful for nested random blocks)
            block += parse_random(lines)
        elif lines[0].startswith('end_random'):
            lines.pop(0)
            if len(block) > 0 and chance > 0 and add_block:
                result.append((chance, block))
            break
        elif lines[0].startswith('percent_chance'):
            if len(block) > 0 and chance > 0 and add_block:
                result.append((chance, block))
            chance = int(lines[0].split(' ')[1])
            if chances >= 100:
                print('  Found unreachable percent_chance')
                add_block = False
            else:
                chances += chance
            block = ''
            lines.pop(0)
        else:
            block += lines.pop(0) + '\n'
    # the result list is empty if we are in the base layer (i.e. in no random block)
    if len(result) == 0:
        return block
    else:
        if result[0][0] == 100:
            print('  Found 100 percent_chance')
            return result[0][1]
        else:
            return_str = ''
            return_str += 'start_random\n'
            for c, b in result:
                return_str += 'percent_chance %d\n' %c
                return_str += b
            return_str += 'end_random\n'
            return return_str

# parse_defines_ifs() looks for #define and if/else/elseif/endif. It mainly removes thoses conditions, which will
# never be reached (-> there is no #define for that case) and rearanges those which are left.
def parse_defines_ifs(lines, def_name, elif_block, defines):
    result = []
    block = ''
    # loop through the lines of the rms file and analyse one by one
    while lines:
        if lines[0].startswith('if'):
            this_condition = lines.pop(0).split(' ')[1]
            print('  Found condition for %s' % this_condition)
            # start a new parser (useful for nested conditions)
            block += parse_defines_ifs(lines, this_condition, 0, defines)
        elif lines[0].startswith('elseif'):
            # this refers to the block before the one found
            if def_name in defines:
                result.append((def_name, elif_block, block))
                def_name = lines.pop(0).split(' ')[1]
                print('  Found elseif condition for %s' % def_name)
                # elif_block = 0 -> if, elif_block = 1 -> elseif, elif_block = 2 -> else
                elif_block = 1
                block = ''
            else:
                print('  Found unreachable condition%s' % ('' if len(def_name) == 0 else ' for %s' % def_name))
                # since if and elseif can be used to build logical NOT conditions, we cannot remove them completly
                # but make them empty
                result.append((def_name, elif_block, ''))
                def_name = lines.pop(0).split(' ')[1]
                elif_block = 1
                block = ''
        elif lines[0].startswith('else'):
            print('  Found else condition')
            lines.pop(0)
            if def_name in defines:
                result.append((def_name, elif_block, block))
                def_name = ''
                elif_block = 2
                block = ''
            else:
                result.append((def_name, elif_block, ''))
                def_name = ''
                elif_block = 2
                block = ''
        elif lines[0].startswith('endif'):
            lines.pop(0)
            if (def_name in defines) or (elif_block == 2):
                result.append((def_name, elif_block, block))
            else:
                print('  Found unreachable condition%s' % ('' if len(def_name) == 0 else ' for %s' % def_name))
                result.append((def_name, elif_block, ''))
            print('  Condition ended')
            break
        elif lines[0].startswith('#define'):
            this_def_name = lines[0].split(' ')[1]
            defines.append(this_def_name)
            print('  Found define %s' % this_def_name)
            block += lines.pop(0) + '\n'
        else:
            block += lines.pop(0) + '\n'
    # the result list is empty if we are in the base layer (i.e. in no condition block)
    if len(result) == 0:
        return block
    else:
        return_str = ''
        for piece in result:
            if piece[1] == 0:
                return_str += 'if %s\n' % piece[0]
            elif piece[1] == 1:
                return_str += 'elseif %s\n' % piece[0]
            else:
                return_str += 'else\n'
            return_str += piece[2]
        return_str += 'endif\n'
    return return_str

def usage():
    print('Usage: mappacker.py [-m] mapfile [mapfile, ...] [mappack_file_name]')
    print('Removes unused lines in rms files like comments, whitespaces and unreachable conditions.')
    print()
    print('The -m flags creates a map pack with name [mappack_file_name] using all the maps listed before.')
    print('When creating a map pack, the maps listed before are also parsed and the files are created.')
    print()
    print('Hint: If something goes wrong, check the output of this tool for a lot of "!!!!!!" and read what')
    print('it has to say.')
    print()
    print('All files created by this tool will be saved in the ./edited/ folder (create it!),')
    print('so no files are overwritten by accident.')
    print()

argc = len(sys.argv)
if argc < 2 :
    usage()
elif argc == 2 and sys.argv[1] == '-m':
    usage()
else:
    comment_regex = re.compile('\/\*.+?\*\/', re.MULTILINE|re.DOTALL)
    percent_regex = re.compile('percent\_chance ([0-9]+) (.+)', re.IGNORECASE)
    cond_regex = re.compile('^if [\S]+\nendif\n', re.IGNORECASE|re.MULTILINE)
    name_regex = re.compile('[^A-Za-z0-9]+')

    maplist = []
    mappack = False
    if sys.argv[1] == '-m':
        mappack = True
        hashlist = []
        mapcontent = []

        maplist = sys.argv[2:-1]
    else:
        maplist = sys.argv[1:]
    for filename_o in maplist:
        print('Open %s' % filename_o)
        with open(filename_o, 'r') as fp:
            content = fp.read()

        print('Remove comments')
        for comment in comment_regex.finditer(content):
            content = content.replace(comment.group(0), '')

        print('Remove unnecessary whitespace')
        content = content.replace('\t', ' ')
        content = content.replace('\r', '')
        while content.find('  ') != -1:
            content = content.replace('  ', ' ')
        content = content.replace('\n ', '\n')
        while content.find('\n\n') != -1:
            content = content.replace('\n\n', '\n')
        content = content.replace(' \n', '\n')

        # TODO: Add missing end_random and endif at the end of the map, this might rescue something.

        print('Remove unnecessary percent_chance')
        num_start_random = content.count('start_random')
        num_end_random = content.count('end_random')
        if num_start_random != num_end_random:
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('  Uneven number of start_random/end_random detected:')
            print('  %d start_random, %d end_random.' % (num_start_random, num_end_random))
            print('  This probably will result in something missing or too much on the map.')
            print('  Please fix the map before using this tool.')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        content = percent_regex.sub(r'percent_chance \1\n\2', content)
        content = parse_random(content.splitlines())

        print('Remove unreachable conditions')
        num_if = content.count('if ') - content.count('elseif ')
        num_endif = content.count('endif')
        if num_if != num_endif:
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('  Uneven number of if/endif detected: %d if, %d endif.' % (num_if, num_endif))
            print('  This will most likely result in complete nonsense.')
            print('  Please fix the map before using this tool.')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        content = parse_defines_ifs(content.splitlines(), '', 0, ['KING_OF_THE_HILL', 'REGICIDE',
                                                                  'TINY_MAP', 'SMALL_MAP', 'MEDIUM_MAP',
                                                                  'LARGE_MAP', 'HUGE_MAP', 'GIGANTIC_MAP'])

        # TODO: also include empty if ... elseif ... [else ...] endif (but only if ALL conditions are empty)
        print('Remove empty if ... endif')
        content = cond_regex.sub('', content)

        filename_w = filename_o
        print('Write %s' % filename_w)
        print()
        with open('edited/%s' % filename_w, 'w') as fp:
            fp.write(content.strip())

        if mappack:
            # make up a unique name for #define
            hashlist.append('MP' + hashlib.md5(filename_o.encode('utf-8')).hexdigest()[0:8].upper() +
                            '_' + name_regex.sub('', filename_o[:-4]).upper())
            mapcontent.append(content.strip())

    if mappack:
        prop = [int(100/len(hashlist))]*len(hashlist)
        for i in range(0, 100 - sum(prop)):
            prop[i] += 1

        mappack_content = ''
        mappack_content += 'start_random\n'
        for h, p in zip(hashlist, prop):
            mappack_content += 'percent_chance %d\n' % p
            mappack_content += '#define %s\n' % h
        mappack_content += 'end_random\n'

        mappack_content += 'if %s\n' % hashlist[0]
        mappack_content += mapcontent[0]
        mappack_content += '\n'
        for h, m in zip(hashlist[1:], mapcontent[1:]):
            mappack_content += 'elseif %s\n' % h
            mappack_content += m
            mappack_content += '\n'
        mappack_content += 'endif'

        print('Write %s' % sys.argv[-1])
        with open('edited/%s' % sys.argv[-1], 'w') as fp:
            fp.write(mappack_content.strip())
