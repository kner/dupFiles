import importlib.machinery
import importlib.util
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

loader = importlib.machinery.SourceFileLoader('dupfiles', str(Path(__file__).with_name('dupFiles')))
spec = importlib.util.spec_from_loader(loader.name, loader)
app = importlib.util.module_from_spec(spec)
loader.exec_module(app)


class DuplicateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.roots = [self.base / str(n) for n in range(1, 4)]
        for root in self.roots:
            root.mkdir()
        app.INDEX = self.base / 'index.json'

    def tearDown(self):
        self.temp.cleanup()

    def file(self, root, name='2026-09-16 09.55.05.jpg'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('test data')
        return path

    def run_app(self, *flags, roots=None, answer=''):
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(out), patch('builtins.input', return_value=answer):
            code = app.main(['--extension', '.jpg', *flags, *map(str, roots or self.roots)])
        return code, out.getvalue()

    def test_delete_13_retains_directory_2(self):
        a = self.file(self.roots[0], 'sub/cb_2026-09-16 09.55.05.JPG')
        b = self.file(self.roots[1])
        c = self.file(self.roots[2], '2026-09-16 09.55.05_cb.jpg')
        other = self.file(self.roots[0], '2026-09-16 09.55.06.jpg')
        code, output = self.run_app('--delete=13', answer='JA')
        self.assertEqual(code, 0)
        self.assertFalse(a.exists())
        self.assertTrue(b.exists())
        self.assertFalse(c.exists())
        self.assertTrue(other.exists())
        self.assertIn('X  [1]', output)
        self.assertIn('-  [2]', output)
        self.assertIn('Keine Duplikate', self.run_app()[1])

    def test_retains_first_when_all_selected(self):
        files = [self.file(r) for r in self.roots]
        self.run_app('--delete=123', answer='JA')
        self.assertEqual([p.exists() for p in files], [True, False, False])

    def test_delete_requires_explicit_confirmation(self):
        files = [self.file(r) for r in self.roots]
        for answer in ('', 'nein', 'ja', 'yes'):
            code, output = self.run_app('--delete=13', answer=answer)
            self.assertEqual(code, 0)
            self.assertIn('2 mit X markierte Dateien', output)
            self.assertIn('Abgebrochen. Keine Dateien gelöscht.', output)
            self.assertTrue(all(p.exists() for p in files))

    def test_delete_eof_and_interrupt_cancel(self):
        files = [self.file(r) for r in self.roots]
        for error in (EOFError, KeyboardInterrupt):
            with redirect_stdout(StringIO()) as out, patch('builtins.input', side_effect=error):
                code = app.main(['--extension', '.jpg', '--delete=13', *map(str, self.roots)])
            self.assertEqual(code, 0)
            self.assertIn('Keine Dateien gelöscht', out.getvalue())
            self.assertTrue(all(p.exists() for p in files))

    def test_no_confirmation_without_planned_deletions(self):
        for root in self.roots:
            self.file(root)
        with redirect_stdout(StringIO()), patch('builtins.input') as prompt:
            app.main(['--extension', '.jpg', *map(str, self.roots)])
            prompt.assert_not_called()

    def test_cache_and_newindex(self):
        self.file(self.roots[0])
        self.run_app()
        self.file(self.roots[1])
        self.assertIn('Keine Duplikate', self.run_app()[1])
        self.assertIn('1 Duplikatgruppen', self.run_app('--newindex')[1])
        self.file(self.roots[2])
        self.assertIn('3 Dateien', self.run_app('--newindex')[1])

    def test_modified_survivor_prevents_deletion(self):
        a = self.file(self.roots[0])
        b = self.file(self.roots[1])
        self.run_app()
        b.write_text('changed after indexing')
        self.run_app('--delete=1')
        self.assertTrue(a.exists())
        self.assertTrue(b.exists())

    def test_overlap_and_symlinks(self):
        a = self.file(self.roots[0])
        (self.roots[1] / a.name).symlink_to(a)
        code, output = self.run_app(roots=[self.base, self.roots[0]])
        self.assertEqual(code, 0)
        self.assertIn('Keine Duplikate', output)

    def test_changed_configuration_rebuilds(self):
        self.file(self.roots[0])
        self.file(self.roots[1])
        self.run_app(roots=[self.roots[0]])
        self.assertIn('1 Duplikatgruppen', self.run_app()[1])

    def test_invalid_delete(self):
        with self.assertRaises(SystemExit) as error:
            self.run_app('--delete=4')
        self.assertEqual(error.exception.code, 2)

    def test_extension_alias_and_default_directory(self):
        import os
        previous = os.getcwd()
        self.file(self.roots[0])
        self.file(self.roots[0], 'cb_2026-09-16 09.55.05.JPG')
        try:
            os.chdir(self.roots[0])
            with redirect_stdout(StringIO()) as out:
                app.main(['--extension==JPG'])
            self.assertIn('1 Duplikatgruppen', out.getvalue())
        finally:
            os.chdir(previous)

    def test_identical_numeric_mp4_names(self):
        for root in self.roots:
            self.file(root, 'nested/1607083502589.mp4')
        self.file(self.roots[0], '1607083502590.mp4')
        self.file(self.roots[1], '1607083502589.mp4.supplemental-metadata.json')
        with redirect_stdout(StringIO()) as out:
            code = app.main(['--extension', '.mp4', *map(str, self.roots)])
        self.assertEqual(code, 0)
        self.assertIn('1 Duplikatgruppen, 3 Dateien', out.getvalue())
        self.assertIn('Epoch (ms): 1607083502589', out.getvalue())

    def test_embedded_epoch_variants(self):
        for epoch in ('1607083502', '1607083502589'):
            for root, name in zip(self.roots, (epoch, 'cb_' + epoch, epoch + '_cb')):
                self.file(root, name + '.jpg')
        code, output = self.run_app()
        self.assertEqual(code, 0)
        self.assertIn('2 Duplikatgruppen, 6 Dateien', output)
        self.assertIn('Epoch (s): 1607083502', output)
        self.assertIn('Epoch (ms): 1607083502589', output)

    def test_epoch_boundaries_and_ambiguity(self):
        for name in ('x16070835025890.jpg', 'x16070835025.jpg',
                     '1607083502_1607083503.jpg',
                     '2026-09-16 09.55.05_1607083502589.jpg'):
            self.assertEqual(app.duplicate_key(name), 'Dateiname: ' + name.casefold())
        self.assertEqual(app.duplicate_key('video1607083502589copy.jpg'),
                         'Epoch (ms): 1607083502589')
        self.assertNotEqual(app.duplicate_key('1607083502589.jpg'),
                            app.duplicate_key('1607083502590.jpg'))

    def test_epoch_delete_confirmation_and_survivor(self):
        files = [self.file(root, name + '.jpg') for root, name in zip(
            self.roots, ('1607083502589', 'cb_1607083502589', '1607083502589_cb'))]
        self.run_app('--delete=123')
        self.assertTrue(all(p.exists() for p in files))
        self.run_app('--delete=123', answer='JA')
        self.assertEqual([p.exists() for p in files], [True, False, False])

    def test_previous_epoch_index_rebuilt(self):
        import json
        self.file(self.roots[0], '1607083502589.jpg')
        self.file(self.roots[1], 'cb_1607083502589.jpg')
        self.run_app()
        data = json.loads(app.INDEX.read_text())
        data['version'] = 2
        for entry in data['entries']:
            entry['key'] = 'Dateiname: ' + Path(entry['path']).name.casefold()
        app.INDEX.write_text(json.dumps(data))
        self.assertIn('1 Duplikatgruppen', self.run_app()[1])

    def test_case_insensitive_plain_names(self):
        self.file(self.roots[0], 'Holiday.jpg')
        self.file(self.roots[1], 'HOLIDAY.JPG')
        self.assertIn('1 Duplikatgruppen', self.run_app()[1])

    def test_old_index_rebuilt(self):
        import json
        self.file(self.roots[0], 'plain.jpg')
        self.file(self.roots[1], 'plain.jpg')
        self.run_app()
        data = json.loads(app.INDEX.read_text())
        data['version'] = 1
        data['entries'] = []
        app.INDEX.write_text(json.dumps(data))
        self.assertIn('1 Duplikatgruppen', self.run_app()[1])

    def test_timestamp_rules(self):
        self.assertEqual(app.timestamp('cb_2026-09-16 09.55.05'), '2026-09-16 09.55.05')
        self.assertIsNone(app.timestamp('2026-02-30 09.55.05'))
        self.assertIsNone(app.timestamp('holiday'))
        self.assertIsNone(app.timestamp('2026-09-16 09.55.05_2026-09-16 09.55.06'))

    def test_delete_string_matches_directory_regex(self):
        a = self.file(self.roots[0], 'CameraUploads/holiday.jpg')
        b = self.file(self.roots[1], 'Archive/holiday.jpg')
        c = self.file(self.roots[2], 'Kopien/holiday.jpg')
        single = self.file(self.roots[0], 'CameraUploads/unique.jpg')
        pattern = '--deleteString=/(CameraUploads|Kopien)/'
        code, output = self.run_app(pattern)
        self.assertEqual(code, 0)
        self.assertIn('2 mit X markierte Dateien', output)
        self.assertTrue(all(path.exists() for path in (a, b, c, single)))
        code, output = self.run_app(pattern, answer='JA')
        self.assertEqual(code, 0)
        self.assertEqual([path.exists() for path in (a, b, c, single)], [False, True, False, True])
        self.assertIn('2 Dateien gelöscht.', output)
        self.assertIn('Keine Duplikate', self.run_app()[1])

    def test_delete_string_matches_filename_and_retains_one(self):
        files = [self.file(root, 'holiday.jpg') for root in self.roots]
        code, output = self.run_app('--deleteString=holiday\\.jpg$', answer='JA')
        self.assertEqual(code, 0)
        self.assertEqual([path.exists() for path in files], [True, False, False])
        self.assertIn('2 Dateien gelöscht.', output)

    def test_delete_string_without_match_does_not_prompt(self):
        files = [self.file(root, 'holiday.jpg') for root in self.roots]
        with redirect_stdout(StringIO()) as out, patch('builtins.input') as prompt:
            code = app.main(['--extension', '.jpg', '--deleteString=HOLIDAY', *map(str, self.roots)])
        self.assertEqual(code, 0)
        prompt.assert_not_called()
        self.assertTrue(all(path.exists() for path in files))
        self.assertIn('0 Dateien gelöscht.', out.getvalue())

    def test_delete_string_invalid_options(self):
        for flags in (('--deleteString=',), ('--deleteString=[',),
                      ('--delete=1', '--deleteString=CameraUploads')):
            with self.subTest(flags=flags), self.assertRaises(SystemExit) as error:
                self.run_app(*flags)
            self.assertEqual(error.exception.code, 2)
        self.assertFalse(app.INDEX.exists())

    def test_group_string_guards_negative_deletion_regex(self):
        camera = self.file(self.roots[0], 'CAMERA/holiday.jpg')
        copy = self.file(self.roots[1], 'Archive/holiday.jpg')
        unmatched = [self.file(root, 'Archive/other.jpg') for root in self.roots]
        code, output = self.run_app('--groupString=(?i)camera',
            '--deleteString=(?i)^(?!.*camera).*$', answer='JA')
        self.assertEqual(code, 0)
        self.assertTrue(camera.exists())
        self.assertFalse(copy.exists())
        self.assertTrue(all(path.exists() for path in unmatched))
        self.assertIn('1 mit X markierte Dateien', output)
        for path in unmatched:
            self.assertIn(f'-  [{self.roots.index(path.parent.parent) + 1}] "{path}"', output)

    def test_group_string_without_match_does_not_prompt(self):
        files = [self.file(root, 'Archive/holiday.jpg') for root in self.roots]
        with redirect_stdout(StringIO()), patch('builtins.input') as prompt:
            code = app.main(['--extension', '.jpg', '--groupString=(?i)camera',
                '--deleteString=(?i)^(?!.*camera).*$', *map(str, self.roots)])
        self.assertEqual(code, 0)
        prompt.assert_not_called()
        self.assertTrue(all(path.exists() for path in files))

    def test_group_string_invalid_options(self):
        for flags in (('--groupString=camera',),
                      ('--deleteString=.*', '--groupString='),
                      ('--deleteString=.*', '--groupString=[')):
            with self.subTest(flags=flags), self.assertRaises(SystemExit) as error:
                self.run_app(*flags)
            self.assertEqual(error.exception.code, 2)
        self.assertFalse(app.INDEX.exists())

    def test_delete_string_rechecks_survivor_before_deletion(self):
        victim = self.file(self.roots[0], 'CameraUploads/holiday.jpg')
        survivor = self.file(self.roots[1], 'Archive/holiday.jpg')
        def confirm(prompt):
            survivor.write_text('changed during confirmation')
            return 'JA'
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()), patch('builtins.input', side_effect=confirm):
            code = app.main(['--extension', '.jpg', '--deleteString=/CameraUploads/', *map(str, self.roots)])
        self.assertEqual(code, 1)
        self.assertTrue(victim.exists())
        self.assertTrue(survivor.exists())

    def test_camera_upload_numbers_are_distinct(self):
        stamp = '2025-11-22 20.55.25'
        names = [stamp + suffix + '.jpg' for suffix in ('', '-1', '-10', '-11', '-12', '-13')]
        self.assertEqual(len({app.duplicate_key(name) for name in names}), len(names))
        files = [self.file(self.roots[0], name) for name in names]
        code, output = self.run_app('--delete=1', answer='JA')
        self.assertEqual(code, 0)
        self.assertIn('Keine Duplikate', output)
        self.assertTrue(all(path.exists() for path in files))

    def test_same_camera_upload_number_matches_variants(self):
        stamp = '2025-11-22 20.55.25-10'
        files = [self.file(root, name + '.jpg') for root, name in zip(
            self.roots, (stamp, 'cb_' + stamp, stamp + '_cb'))]
        code, output = self.run_app('--delete=13', answer='JA')
        self.assertEqual(code, 0)
        self.assertIn('1 Duplikatgruppen, 3 Dateien', output)
        self.assertEqual([path.exists() for path in files], [False, True, False])

    def test_old_camera_upload_index_rebuilt(self):
        import json
        for suffix in ('-1', '-10'):
            self.file(self.roots[0], '2025-11-22 20.55.25' + suffix + '.jpg')
        self.run_app()
        data = json.loads(app.INDEX.read_text())
        data['version'] = 3
        for entry in data['entries']:
            entry['key'] = 'Zeitstempel: 2025-11-22 20.55.25'
        app.INDEX.write_text(json.dumps(data))
        code, output = self.run_app('--delete=1', answer='JA')
        self.assertEqual(code, 0)
        self.assertIn('Index neu aufgebaut', output)
        self.assertIn('Keine Duplikate', output)


if __name__ == '__main__':
    unittest.main()
