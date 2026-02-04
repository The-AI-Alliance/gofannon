# Architecture / Services

This page provides an overview of the Gofannon architecture and its core services.

## Overview

Gofannon is designed as a modular system for rapidly prototyping AI agents and their associated web UIs. It follows a microservices-based approach to ensure that AI tools and agent behaviors are portable and framework-independent, adhering to the principle of "Stop Rewriting AI Tools for Every Framework."

## Core Services

<!-- *Documentation coming soon...* -->
Gofannon consists of several interconnected services that work together to provide a seamless prototyping experience:
- WebUI (Frontend): A React-based application built with Material-UI (MUI). It provides the visual interface for building agent flows, configuring tool manifests, and interacting with chat-driven experiences. 

- User Service (API): Located in webapp/packages/api/user-service. This is a FastAPI-based backend that handles user authentication, profile management, and serves as the primary gateway for persisting agent configurations.

- Docusaurus Website: Located in the website/ directory. This is the public-facing documentation and info site. It is built using Docusaurus and provides the guides, API references, and community information.

- Tool Manifest System: A core logic layer that standardizes tool definitions. It allows agents to leverage tools (like Wikipedia, Math, or custom scrapers) across different frameworks (LangChain, Llama Stack, etc.) by using a unified manifest format.

## System Architecture

*Detailed architecture diagrams and descriptions will be added here.*


## Service Interactions

*Information about how services communicate and interact will be documented here.*
