# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo provides the tools, skills and MCP servers that let Claude Code act as a job application agent. Target capabilities (from README):

- Search for job openings
- Write cover letters
- Track application status
- Update that tracking from the email inbox

## Current state

Freshly scaffolded with `uv init`: only `hello.py` (placeholder entry point) and `pyproject.toml` (Python >=3.12, no dependencies). No tests, linter, or package layout yet. Update this file as those are added.

## Commands

- Run: `uv run hello.py`
- Add a dependency: `uv add <package>`
