"""Fingerprint Jetson worker package setup."""

from pathlib import Path

from setuptools import find_packages, setup


README = Path(__file__).with_name("README.md").read_text(encoding="utf-8")


setup(
    name="fingerprint-jetson-worker",
    version="2.1.0",
    description="Installable fingerprint worker for Jetson-based verification nodes",
    long_description=README,
    long_description_content_type="text/markdown",
    author="MDGT",
    python_requires=">=3.10",
    packages=find_packages(include=["app*", "gui*"]),
    py_modules=["cli"],
    install_requires=[
        "aiofiles>=23,<25",
        "click>=8.1,<9",
        "cryptography>=41,<46",
        "fastapi>=0.95,<1.0",
        "httpx>=0.25,<1.0",
        "numpy>=1.24,<2.0",
        "paho-mqtt>=1.6,<2.0",
        "pillow>=10,<12",
        "pydantic>=2.5,<3.0",
        "pydantic-settings>=2.1,<3.0",
        "python-dateutil>=2.8,<3.0",
        "python-multipart>=0.0.6,<1.0",
        "pyusb>=1.2.1,<2.0",
        "pyyaml>=6,<7",
        "requests>=2.31,<3.0",
        "uvicorn[standard]>=0.23,<1.0",
        "websocket-client>=1.7,<2.0",
        "websockets>=10,<16",
    ],
    extras_require={
        "ai": [
            "onnxruntime>=1.17.3,<1.18",
            "faiss-cpu>=1.7.4,<2.0",
            "opencv-python>=4.8,<5.0",
        ],
        "jetson": [
            "onnxruntime>=1.17.3,<1.18",
            "faiss-cpu>=1.7.4,<2.0",
            "opencv-python>=4.8,<5.0",
            # TensorRT is expected from JetPack on the target device.
        ],
        "onnx": [
            "onnxruntime>=1.17.3,<1.18",
        ],
        "faiss": [
            "faiss-cpu>=1.7.4,<2.0",
        ],
        "dev": [
            "pytest>=8,<9",
            "pytest-asyncio>=0.23,<1.0",
        ],
        "ssh": [
            "asyncssh>=2.14,<3.0",
        ],
        "gui": [
            'PyQt6>=6.5,<7.0; platform_machine != "aarch64"',
        ],
    },
    entry_points={
        "console_scripts": [
            "fingerprint-worker-api=app.main:main",
            "fingerprint-worker-cli=cli:run_cli",
            "fingerprint-worker-gui=gui.__main__:main",
        ],
    },
)
