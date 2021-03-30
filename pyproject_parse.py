# Let PIP be PIP!

# Uses the pyproject.toml file to generate an equivlent requirements.txt file
# Should be run any time a requirement is changed

# Based on the "Version constraints" section of the "Dependency specification" docs:
# https://python-poetry.org/docs/dependency-specification/

# Copyright: Elliot Gerchak

with open('pyproject.toml') as f_obj:
    py_project_text = f_obj.read()

# the contents (string) that will be in the 'requirements.txt' file
req_txt = ''

# split 'pyproject.toml' into ~4 sections (break on every double-line break)...
# sections: projet meta, 'dependencies', 'dev-dependencies', and 'build-system'
for section in py_project_text.split('\n\n'):
    # break the section at the first line-brreak to get the header AND contents
    section_title, section_contents = section.split('\n', 1)

    # find the 'dependencies' section
    if section_title == '[tool.poetry.dependencies]':
        # proccess each line as a dependency
        for depend in section_contents.split('\n'):
            # parse out the dependency names and version strings
            dep_name, dep_vers = depend.split(' = ')[:2]
            # strip the double-quotes from the version info
            dep_vers = dep_vers.strip('"')

            # currently only suports the carrot operator (and not a tilda)
            caret = dep_vers.startswith('^')
            if caret:
                # remove the first char and split up the version number
                dep_vers = dep_vers[1:]
                ver_split = dep_vers.split('.')

                # generate a maximum version number
                # (based on the official Poetry Docs)
                max_ver = []
                for ver_part in ver_split:
                    if ver_part.strip('0'):
                        max_ver.append(str(int(ver_part) + 1))
                        break
                    else:
                        max_ver.append(ver_part)

                # fill in with zeros and convert back to string
                max_ver += ['0'] * (len(ver_split) - len(max_ver))
                max_ver_str = '.'.join(max_ver)

            # generate a line of text that is suitable for this packages'
            # version requirements in a (pip -r) 'requirements.txt' file
            require_ln = f'{dep_name} {">=" if caret else "=="} {dep_vers}'
            if caret:
                # add in the maximum version number
                require_ln += f', < {max_ver_str}'

            # ignore the line about the python version...
            if dep_name != 'python':
                # add the line to our list
                req_txt += require_ln + '\n'
            else:
                # ...but print it here so we can see it.
                print('Runtime:', require_ln)
                print('-' * 30)

        # save it and print the output
        print('\nSaved to "requirements.txt":')
        print('  ' + req_txt.rstrip('\n').replace('\n', '\n  '))
        with open('requirements.txt', 'w', encoding='utf-8') as f_obj:
            f_obj.write(req_txt)

        # no need to proccess the rest of the document
        break
else:
    print('Error: Could not find list of dependencies.')
