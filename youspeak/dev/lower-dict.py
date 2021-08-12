import re

with open('english.dict') as f: # located in resources/aligner
    contents = f.read()

lines = re.findall(r'(.*?)\s(.*?)\n', contents)
newlines = [(line[0].strip().lower(),line[1].strip()) for line in line]

with open('english_guava.dict', 'w+') as out_file:
    for line in newlines:
        out_file.write('{0}\t{1}\n'.format(line[0],line[1]))
