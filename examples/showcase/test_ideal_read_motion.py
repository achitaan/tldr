import json
import sys
import unittest
from pathlib import Path


HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))

from full_export import context_source_refs,lesson_context_object,manifest_context_object
from full_render import chapter_key
from ideal_read_motion import CONTEXT_IDS,EDGE_X,ideal_context_objects,ideal_read_state


class IdealReadMotionTests(unittest.TestCase):
    def test_explicit_original_example_inputs(self):
        state=ideal_read_state(0,prior_register=19,selected_address=16,selected_value=42)
        self.assertEqual((state['register_value'],state['selected_address'],state['selected_value']),(19,16,42))
        self.assertIn('not an analog delay simulation',state['illustration_scope'])

    def test_edge_three_precedes_storage_cue(self):
        address_motion=ideal_read_state(3,prior_register=19,selected_address=16,selected_value=42)
        return_motion=ideal_read_state(7,prior_register=19,selected_address=16,selected_value=42)
        before=ideal_read_state(8,prior_register=19,selected_address=16,selected_value=42)
        after=ideal_read_state(9,prior_register=19,selected_address=16,selected_value=42)
        self.assertTrue(address_motion['address_token_motion'])
        self.assertEqual((return_motion['return_token_motion'],return_motion['register_value']),(True,19))
        self.assertEqual((before['cursor_edge'],before['register_value'],before['storage_visible']),(3,19,False))
        self.assertEqual((after['cursor_edge'],after['register_value'],after['storage_visible']),(3,42,True))

    def test_prediction_replay_hides_then_reveals_answer(self):
        completed=ideal_read_state(12)
        replay=ideal_read_state(13)
        reveal=ideal_read_state(14)
        self.assertEqual((completed['register_value'],completed['cursor_edge']),(42,3))
        self.assertEqual((replay['register_value'],replay['cursor_edge'],replay['returned_data_available']),(19,None,False))
        self.assertTrue(replay['answer_hidden'])
        self.assertEqual((reveal['register_value'],reveal['cursor_edge'],reveal['storage_visible']),(42,3,True))

    def test_every_interval_exports_stable_context_and_source_identity(self):
        asset={'ref':'r4','sha256':'a'*64,'crop':{'x':.045,'y':.17,'width':.89,'height':.31}}
        for sentence in (0,2,3,4,5,6,7,8,9,10,11,13,14):
            objects=ideal_context_objects(ideal_read_state(sentence))
            self.assertEqual(tuple(obj['id'] for obj in objects),CONTEXT_IDS)
            self.assertEqual(objects[0]['provenance'],'original_source')
            self.assertTrue(all(obj['provenance']=='conceptual' for obj in objects[1:]))
            spec_objects=[lesson_context_object(obj,'r4') for obj in objects]
            self.assertEqual(context_source_refs(objects,'r4','p99'),['r4','p99'])
            self.assertTrue(all('Illustrative logical example:' in obj['label'] for obj in spec_objects[1:]))
            self.assertTrue(all('Illustrative logical example:' in obj.get('text',obj['label']) for obj in spec_objects[1:]))
            exported=manifest_context_object(objects[0],asset)
            self.assertEqual((exported['source_ref'],exported['asset_sha256'],exported['crop']),('r4','a'*64,asset['crop']))
            self.assertEqual(lesson_context_object(objects[0],'r4')['source_ref'],'r4')

    def test_reviewed_cursor_coordinates_remain_stable(self):
        self.assertEqual(EDGE_X,{1:.2115,2:.5325,3:.8525})

    def test_helper_digest_only_invalidates_ideal_chapter(self):
        assets={'pages':{'13':{'sha256':'source'},'5':{'sha256':'other'}}}
        ideal={'id':'ideal','audio':'ideal.wav','pages':[13]}
        ownership={'id':'ownership','audio':'ownership.wav','pages':[5]}
        def digester(helper_hash):
            return lambda path: helper_hash if Path(path).name=='ideal_read_motion.py' else f'fixed:{Path(path).name}'
        self.assertNotEqual(chapter_key(ideal,assets,digester('helper-a')),chapter_key(ideal,assets,digester('helper-b')))
        self.assertEqual(chapter_key(ownership,assets,digester('helper-a')),chapter_key(ownership,assets,digester('helper-b')))

    def test_existing_practice_and_reveal_times_are_preserved(self):
        narration=json.loads((ROOT/'artifacts/ece224-lesson/audio/narration.json').read_text(encoding='utf-8'))
        beat=next(item for item in narration['beats'] if item['id']=='ideal')
        self.assertEqual(beat['practice'][0]['after_sentence'],13)
        self.assertAlmostEqual(beat['cues'][13]['end_seconds']+.5,84.17458333333333)
        self.assertAlmostEqual(beat['cues'][14]['start_seconds'],86.67458333333333)


if __name__=='__main__':unittest.main()
