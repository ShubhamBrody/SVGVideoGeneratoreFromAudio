"""Test configuration.

Force the offline mock provider so tests are deterministic and never touch the
network, regardless of any OPENAI_API_KEY present in the environment.
"""
import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ["OPENAI_API_KEY"] = ""
