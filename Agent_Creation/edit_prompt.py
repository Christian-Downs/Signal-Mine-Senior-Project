def write_file(file_name, value):
    with open("prompts/"+str(file_name), 'W') as file:
        file.write(value)
