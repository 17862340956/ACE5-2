# Undo only the two DDK edits that suppress export/CRC resolution.
{
    line = $0
    if (line ~ /^[ \t]*\/\/[ \t]*check_exports\(mod\);[ \t]*$/)
        sub(/\/\/[ \t]*/, "", line)
    if (line ~ /^[ \t]*\/\/[ \t]*s->module[ \t]*=[ \t]*exp->module;[ \t]*$/)
        sub(/\/\/[ \t]*/, "", line)
    print line
}
