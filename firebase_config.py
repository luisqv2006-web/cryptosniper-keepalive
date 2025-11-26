import os
import firebase_admin
from firebase_admin import credentials, firestore

# =========================================
# CONFIGURACIÓN FIREBASE (SEGURA CON ENV)
# =========================================

cred = credentials.Certificate({
    "type": "service_account",
    "project_id": "cryptosniper-keepalive-1",
    "private_key": os.getenv(-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDZsUZa6w7iJRli\nZcSQ901+PXLlApv4/+jvpK8qTu0A9tkXJGwPUGfEniSQFPXCbTDtDc/1fzp9iXKM\nk6PN8f2Bj3KsbZ+7q6pUod+hA+atncwooo62J//uLW4Ms+fGIgg1wkAmq2PS2iHP\nFDA/AgZ3gSrkdbLI+XA8qXVz5+A8Y2gxMRG6aDHN21+jgZnti0vIQd8hKkHL94ku\nOoASvD81MMZkYGURdyUCXGCu78m7rEemzjFWiM1srWaowHoH82ihEStKefekpaq9\nc5P6pIjoRaVUrYEGn3zWpLaD7qkkNTHaltqQ+qwig1OXW5OSalD7IzJla+9wOayQ\njCEJaYNXAgMBAAECggEAUKe7Su1DPuuC66+L9DAEYKzwuEPOuSNL0RpBohnK+uv6\ng/YFKWlfgPwczNtPMOGW2oWfErS4XZHCxK3g52lsxQd6c8NMBtL0EVZGTlhtK89G\nuJl96aSJUNw5JXC0g3bRduWJMiqXGiSimSBAPeAIuFc9pparDoZInNkmQLLdJFH7\nbLZGkpiHuP8AokhsRXaHtlRoi/5w5w7y1wCTuB9QIOLgv0jSuXb3748JEryzc0y3\nwPc54mxM7ynWQTX1z/DLxmFkEY0Wz6CebaxdiwQ7mLXaH9ZA7qZ4roXFwy4oLYMu\nQo+pz5or2K+8/uvdSWOAMBCfEIq1dyalsLgALTtPnQKBgQDxHQg/TfweFU8J575W\nP1eyIn10QdHrWH9oG4yzR7pElurhECytOGI4VgnXySGx69TxHDkIfq6B4tO88Y2D\nU2crr5v72FfIdt3v4NGOpVG1uSXrQbXEHw8vnemRkFNYMJh+mLHW48CgWNkIgFR5\nFRE/X6PwtyhVhdHZceGUX4YvCwKBgQDnIg7s40hu3BCwv4q0sorHSM7sxMF3522W\nVouMdnaI11+219SpjcwgR+aL77vR7Brtv0g2hsO2pS92eeJLK+4uKPhfW/BX+7ZS\npXwO9y/5TYvbj9yIu8Y5wmAv08Ms8LAbZg7S8bAcyNo9sYFeV31/1B1z+BlgXOQQ\nrTHxoFNcZQKBgQCBH5QgGspu7ehzHIlhNPDo8/GNhgY+bBlnDoHuLPaC7vOAbiIO\n7ggjtWf2CL+jwfE64mtksjsQUgIkyJOJhevViGkXmUeBkq7OXO683qoAkNPOxlTq\nX9vJG19PViRcMUIpYeqzcyrgdFReaiNS6MZg0v4/1kaiblTwhz1QMUvx+wKBgEtB\nAY8LaVf++sgxdR3kS98ay5S3cy5xAXNDdmgjYfCn/xfvKeSSsHWKM3w4b/SnZRUn\nhIGMW0iqe8udX5qOERyiZkvWCWj8IZ7DFqNgxBPtta2lJ261hJLlwJ+R2ShWrWAe\nWJFB889LbhNMKgzne4sVKwnJK6n+VJtBaNN9GecpAoGBAOo/SRMiEcsqP51lklG9\nBJMGCRHXF1p9Y8HqUVD7Pa8/QYXb0caN7/1BF8yFe8U6ApZbAe/ja0vgaHB0DvtU\nOcVziDFFMd7iTFhYNmM7NvK0j4YLZjG8pp8b4zrdwIOiDaMqWwNv4LFydzJ1/Q4D\nKFiviXmEOJ6+TjMd1ygycBNU\n-----END PRIVATE KEY-----\n).replace("\\n", "\n"),
    "client_email": "firebase-adminsdk-fbsvc@cryptosniper-keepalive-1.iam.gserviceaccount.com",
    "token_uri": "https://oauth2.googleapis.com/token",
})

firebase_admin.initialize_app(cred)
db = firestore.client()
