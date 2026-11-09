import base64,hmac,json,time,unittest
from hashlib import sha256
from verify_event_access import verify_issue
class EventAccess(unittest.TestCase):
    secret='test-secret-with-at-least-thirty-two-characters'
    def body(self,**changes):
        event={'title':'Robotics workshop'}
        proof={'purpose':'event-submission','domain':'esrarobotics.eu','event':event,'expires':time.time()+60,**changes}
        enc=lambda value:base64.urlsafe_b64encode(value).decode().rstrip('=')
        data=enc(json.dumps(proof,separators=(',',':')).encode())
        token=data+'.'+enc(hmac.new(self.secret.encode(),data.encode(),sha256).digest())
        return '### Event details\n\n```json\n'+json.dumps(event)+'\n```\n\n### ESRA verification\n\n'+token
    def test_valid(self):self.assertTrue(verify_issue(self.body(),self.secret))
    def test_invalid(self):
        for body in [self.body(expires=1),self.body(domain='attacker.example'),self.body().replace('Robotics workshop','Changed workshop'),'No attestation']:
            with self.assertRaises(ValueError):verify_issue(body,self.secret)
        with self.assertRaises(ValueError):verify_issue(self.body(),'')
if __name__=='__main__':unittest.main()
