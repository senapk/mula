
function LineBreak(el)
  if inside_block then
    return el  -- mantém a quebra normal dentro de blocos
  else
    return pandoc.Str('  \n')
  end
end
