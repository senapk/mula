from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from mula.__main__ import app
from mula.Add import Add, AddOptions
from mula.operation_state import OperationState
from mula.readme_manifest import load_readme_groups
from mula.workflow import PublishWorkflow


class ReadmeManifestTest(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        for label in ('labs/a', 'labs/b'):
            path = self.repo / label
            path.mkdir(parents=True)
            (path / 'README.md').write_text('# Task')
        self.source('## First <!-- @first -->\n- [x] [A](labs/a/README.md)\n')

    def source(self, value):
        (self.repo / 'README.md').write_text(value)

    def options(self, **kwargs):
        return AddOptions(course='42', repo=str(self.repo), from_readme=True, **kwargs)

    def test_groups_order_empty_inactive_and_markdown(self):
        self.source('''---
args: example
---
# Index
## First <!-- @first -->
- [x] [A](labs/a/README.md)
- [ ] [Again](labs/a/README.md)
### Nested
- [B][b]
- [Remote](https://example.org/README.md)
```md
## Fake <!-- @fake -->
- [Fake](missing/README.md)
```
## Skip <!-- @skip active=0 -->
- [Missing](missing/README.md)
## Empty <!-- @empty -->
## Last <!-- @last -->
- [ ] [A](labs/a/README.md)
## Unmarked
- [Missing](missing/README.md)

[b]: labs/b/README.md
''')
        for start in (0, 1, 3):
            groups = load_readme_groups(self.repo, start)
            self.assertEqual([(g.marker, g.section, g.labels) for g in groups],
                             [('first', start, ('labs/a', 'labs/b')),
                              ('empty', start + 1, ()), ('last', start + 2, ('labs/a',))])

    def test_invalid_sources_and_paths(self):
        sources = ['---\nunterminated', '# No groups', '## Empty <!-- @empty -->']
        sources += [f'## Group <!-- @g -->\n- [Task]({href})'
                    for href in ('../outside/README.md', '/absolute/README.md',
                                 '%2E%2E/outside/README.md', 'missing/README.md')]
        for source in sources:
            with self.subTest(source=source):
                self.source(source)
                with self.assertRaises(ValueError):
                    self.options().validate()
        (self.repo / 'README.md').unlink()
        with self.assertRaisesRegex(ValueError, 'Cannot read'):
            load_readme_groups(self.repo)

    def test_symlink_escape_is_rejected(self):
        with TemporaryDirectory() as outside:
            external = Path(outside) / 'README.md'
            external.write_text('# External')
            target = self.repo / 'labs/a/README.md'
            target.unlink()
            target.symlink_to(external)
            with self.assertRaisesRegex(ValueError, 'outside'):
                load_readme_groups(self.repo)

    def test_cli_exclusive_sources_and_readme_options(self):
        with patch('mula.cli_add.Add.add') as add, \
             patch('mula.credentials.Credentials.fill_empty') as auth:
            base = ['add', '-c', '42', '-r', str(self.repo)]
            for args in ([], ['--from-readme', 'labs/a']):
                result = CliRunner().invoke(app, base + args)
                self.assertEqual(result.exit_code, 2, result.output)
            auth.assert_not_called()
            result = CliRunner().invoke(app, base + ['--from-readme', '-S', '1', '-l', 'py'])
            self.assertEqual(result.exit_code, 0, result.output)
            options = add.call_args.args[0]
            self.assertTrue(options.from_readme)
            self.assertEqual([(t.section, t.label, t.drafts) for t in options.tasks()], [(1, 'labs/a', 'py')])

    def test_preview_validation_and_resume_use_resolved_tasks(self):
        self.source('## First <!-- @first -->\n- [A](labs/a/README.md)\n## Empty <!-- @empty -->')
        structure = Mock(section_labels=['General', 'Operations', 'Empty'])
        structure.get_number_of_sections.return_value = 3
        checkpoint = self.repo / 'operation.json'
        checkpoint.write_text('previous')
        credentials = Mock(url='https://saved.example')
        credentials.get_course.return_value = '42'
        output = StringIO()
        with patch('mula.operation_state.checkpoint_path', return_value=checkpoint), \
             patch('mula.Add.Credentials.load_credentials', return_value=credentials), \
             patch('mula.Add.StructureLoader.load', return_value=structure), \
             patch.object(OperationState, 'open_in_vscode') as editor, \
             patch.object(PublishWorkflow, 'execute') as execute:
            with redirect_stdout(output):
                Add.add(self.options(section=1, dry_run=True))
            self.assertIn('First (@first) -> Section 1: Operations', output.getvalue())
            self.assertIn('2 active groups, 1 tasks', output.getvalue())
            self.assertEqual(checkpoint.read_text(), 'previous')
            structure.get_number_of_sections.return_value = 2
            with self.assertRaisesRegex(ValueError, 'Empty.*section 2'):
                Add.add(self.options(section=1))
            editor.assert_not_called()
            execute.assert_not_called()
            self.assertEqual(checkpoint.read_text(), 'previous')
            structure.get_number_of_sections.return_value = 3
            Add.add(self.options(section=1, drafts='py'))
            saved = OperationState.load()
            self.assertEqual([(t.section, t.label) for t in saved.tasks], [(1, 'labs/a')])
            (self.repo / 'README.md').unlink()
            with patch('mula.workflow.Credentials.load_credentials', return_value=credentials), \
                 patch('mula.workflow.StructureLoader.load', return_value=structure):
                PublishWorkflow.resume()
            resumed = execute.call_args.args[0]
            self.assertEqual([(t.section, t.label, t.drafts) for t in resumed.tasks], [(1, 'labs/a', 'py')])
