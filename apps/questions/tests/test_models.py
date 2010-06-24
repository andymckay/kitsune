from nose.tools import eq_

from questions.models import Question, QuestionMetaData
from questions.tests import TestCaseBase


class TestQuestionMetadata(TestCaseBase):
    """Tests handling question metadata"""

    def setUp(self):
        super(TestQuestionMetadata, self).setUp()

        # add a new Question to test with
        question = Question(title='Test Question',
                            content='Lorem Ipsum Dolor',
                            creator_id=1)
        question.save()
        self.question = question

    def tearDown(self):
        super(TestQuestionMetadata, self).tearDown()

        # remove the added Question
        self.question.delete()

    def test_add_metadata(self):
        """Test the saving of metadata."""
        metadata = {'version': u'3.6.3', 'os': u'Windows 7'}
        self.question.add_metadata(**metadata)
        saved = QuestionMetaData.objects.filter(question=self.question)
        eq_(saved.count(), 2)
        eq_(saved[0].name, 'version')
        eq_(saved[0].value, u'3.6.3')
        eq_(saved[1].name, 'os')
        eq_(saved[1].value, u'Windows 7')

    def test_metadata_property(self):
        """Test the metadata property on Question model."""
        self.question.add_metadata(crash_id='1234567890')
        eq_('1234567890', self.question.metadata['crash_id'])