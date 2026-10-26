# creality-print-mcp

[English](README.md)

Servidor [MCP](https://modelcontextprotocol.io) que permite a assistentes de IA (Claude, Gemini/Antigravity, Cursor…) **ler, auditar e editar os perfis do Creality Print** e **medir, redimensionar e rotacionar modelos 3D**.

O Creality Print é um fork do OrcaSlicer, que por sua vez é fork do Bambu Studio, e os três usam o mesmo formato de perfil. **OrcaSlicer e Bambu Studio também funcionam.**

> "Por que o suporte está grudando na peça?" → o assistente audita o perfil de processo, mostra que `support_top_z_distance` vem herdado do perfil do fabricante e está pequeno demais para a altura de camada, e corrige com backup.

## Ferramentas

| Ferramenta | O que faz |
|---|---|
| `list_profiles` | Lista seus perfis de processo, filamento e máquina, com o perfil de origem de cada um |
| `get_profile` | Devolve os valores **efetivos** do perfil, seguindo toda a cadeia `inherits` até o perfil do fabricante (ou só o que você alterou) |
| `audit_profile` | Aponta causas comuns de falha: infill cruzado batendo no bico, suporte fundindo ou marcando a peça, parede ondulada, superfície ruim sob o suporte. Informa se cada valor é seu ou herdado |
| `set_profile_parameter` | Altera um parâmetro com backup automático. Mantém campos em lista como lista e recusa chaves inexistentes (erro de digitação) e chaves de identidade |
| `list_backups` / `restore_backup` | Desfaz qualquer alteração |
| `get_model_dimensions` | Tamanho (X/Y/Z mm), volume, malha fechada e faces de `.stl`, `.obj`, `.3mf` |
| `scale_model` | Escala uniforme por percentual, fator ou altura desejada, em um arquivo novo |
| `rotate_model` | Rotação em X/Y/Z para melhorar o apoio na mesa e reduzir suportes, em um arquivo novo |

### Por que a herança importa

O perfil salvo guarda **só o que você mudou**. O resto vem do perfil do fabricante via `inherits`. Uma ferramenta que lê só o arquivo do usuário enxerga uns 10 de cerca de 270 parâmetros e precisa adivinhar o resto. Este servidor resolve a cadeia como o fatiador faz, inclusive quando vários fabricantes têm um perfil base com o mesmo nome.

## Requisitos

- Python 3.10+ e [uv](https://docs.astral.sh/uv/) (recomendado)
- Creality Print 6/7, OrcaSlicer ou Bambu Studio instalado e aberto ao menos uma vez
- Windows, macOS ou Linux. As pastas padrão são detectadas sozinhas; até agora o desenvolvimento e o teste com dados reais foram em **Windows + Creality Print 7.3**

## Instalação

### Claude Code

```bash
claude mcp add --scope user creality-print -- uvx --from git+https://github.com/MadCrow69/creality-print-mcp creality-print-mcp
```

> **Windows PowerShell:** o PowerShell descarta o `--` antes de passar os argumentos ao `claude`, que então falha com `unknown option`. Rode via `cmd`:
> `cmd --% /c claude mcp add --scope user creality-print -- uvx --from git+https://github.com/MadCrow69/creality-print-mcp creality-print-mcp`

### Claude Desktop, Antigravity, Cursor e outros clientes com config JSON

```json
{
  "mcpServers": {
    "creality-print": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/MadCrow69/creality-print-mcp", "creality-print-mcp"]
    }
  }
}
```

### OrcaSlicer ou Bambu Studio

Adicione à entrada acima:

```json
"env": { "SLICER": "orca" }
```

## Configuração

| Variável | Padrão | Uso |
|---|---|---|
| `SLICER` | `creality` | `creality`, `orca` ou `bambu` |
| `SLICER_CONFIG_DIR` | automático | Pasta que contém `user/` e `system/`. Use em instalação portátil ou para fixar uma versão do Creality Print (ex: `…\Creality Print\7.3`) |
| `CREALITY_PRINT_MCP_BACKUP_DIR` | `~/.creality-print-mcp/backups/<slicer>` | Onde ficam os backups dos perfis |

## Segurança

- Toda edição de perfil faz backup com data e hora antes e grava de forma atômica.
- As ferramentas de modelo sempre geram um arquivo **novo** e recusam sobrescrever o original.
- Nomes de perfil são validados, então não dá para acessar caminhos fora da pasta de perfis.
- **Feche o fatiador antes de editar perfis** (ou reinicie depois). Aberto, ele pode sobrescrever o arquivo ao salvar o próprio estado.
- Perfis sincronizados com a nuvem: o servidor não mexe nos metadados `.info`. Se a sincronização trouxer uma versão antiga de volta, use `restore_backup` ou reaplique a alteração.

## Desenvolvimento

```bash
git clone https://github.com/MadCrow69/creality-print-mcp
cd creality-print-mcp
uv sync
uv run pytest
uv run ruff check .
```

Os testes usam árvores de perfis sintéticas e nunca tocam nos dados reais do fatiador.

## Licença

[MIT](LICENSE)

Projeto sem vínculo com Creality, OrcaSlicer ou Bambu Lab. Os nomes de produtos são marcas de seus respectivos donos.
